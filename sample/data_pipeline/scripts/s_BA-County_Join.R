############################################################################
### s_BA-County_Join: Spatial join between BA and county files
###
### Description: This script loads and joins together the BA shapefile and 
###              yearly county shapefiles, assigning counties to BAs until 
###              all counties are assigned a BA (in the contiguous 48 states)
###              via assignment rules applied to spatial overlaps. This is done
###              via the f_ba_make function below for each year fed to this 
###              script from snakemake. This is run for each year to deal with
###              changes in county definitions over time (e.g. Connecticut)
###              
### - Inputs
###   * EIA_BA_Details.csv
###   * EIA_BASR-Details.csv
###   * EIA_BA.gpkg
### - Outputs
###   * EIA_BA-County.csv
###
### Date Commented: 7/9/24
############################################################################

#####
### Set-up: Loading packages (included in Conda environment)
#####
libraries <- c("tidyverse", "data.table", "tigris", "sf", 
               "readxl", "here")
invisible(lapply(libraries, library, character.only = TRUE))

### Ensure working directory pointed at Snakefile location
here::i_am("Snakefile")

### Load Snakemake parameters
v.years.sm <- snakemake@params$years_sm
#v.years.sm <- 2018:2022

################################################################################
### Step 1: Merge BA shapefile to counties for each year
################################################################################

#####
### Create function for spatial join and run for snakemake-defined years
#####

f_ba_make <- function(i.year){
  
  #####
  ### Load shapefiles
  #####
  
  ### Set CRS
  v.crs  <- "ESRI:102008"
  
  ### Load Counties (from API), set CRS, and calculate county size
  sf.county  <- tigris::counties(cb = TRUE,
                                 year = i.year) %>%
    st_transform(v.crs)                        %>%
    mutate(FIPS_cnty    = GEOID)               %>%
    mutate(Area_m2  = as.numeric(round(st_area(.),0))) %>%
    select(FIPS_cnty, Area_m2)
  
  ### Load Balancing Authority
  sf.ba <- st_read(here("outputs", "shapefiles", "EIA_BA.gpkg"),
                   layer = "BA")
  
  #####
  ### Load all details files
  #####
  dt.ba_detail <- fread(here("outputs", "crosswalks", "EIA_BA_Details.csv"))
  dt.basr_detail <- fread(here("outputs", "crosswalks", "EIA_BASR-Details.csv"))
  
  ################################################################################
  ### Note: Intersect BA boundaries w/ counties
  ### Assignment Rules:
  #   - if >50% overlap, assign to BA
  #   - if multiple overlap, assign all majority overlapping BAs
  #   - if no BA assignment, assign to largest
  #   - if BA goes unassigned, assign to county w/ largest
  ################################################################################
  
  #####
  ### Intersect county and ba shapefiles; create indicators for each assignment rule
  ###   - Intersect county and BA
  ###   - Calculate share of overlaps for intersected geometries
  ###   - If more than half of county in BA, assign
  ###   - If unassigned, assign BA with max share to county
  #####
  sf.ba_cnty <- st_intersection(sf.county, sf.ba)
  sf.ba_cnty_assign <- copy(sf.ba_cnty) %>%
    mutate(AreaInt_m2 = as.numeric(round(st_area(.),0))) %>%
    as.data.table() %>%
    .[,!c("geometry")] %>%
    .[,FIPS_st := str_sub(FIPS_cnty, end = 2)] %>%
    .[,BA_Share   := round(AreaInt_m2/Area_m2, 4)] %>%
    .[,Rule1 := ifelse(BA_Share > 0.5,
                       1,
                       0)] %>%
    .[,NoRule1 := ifelse(max(Rule1, na.rm = TRUE)==1,
                         0,
                         1),
      by = "FIPS_cnty"] %>%
    .[,Rule2 := ifelse(max(BA_Share, na.rm= TRUE) == BA_Share,
                       1,
                       0),
      by = "FIPS_cnty"] %>%
    .[,Assign := ifelse((Rule1 == 1) | (Rule1 == 0 & Rule2 == 1),
                        1,
                        0)] %>%
    .[,c("FIPS_cnty", "FIPS_st", "Region_Name", 
         "BA_Code", "BA_Share", 
         "Rule1", "Rule2", "Assign")] %>%
    .[,Rule3 := 0]
  
  #####
  ### Check 1: Every BA that passes filter is assigned; for each, find assign
  #####
  v.ba        <- unique(dt.ba_detail$BA_Code)
  v.ba_assign <- unique(sf.ba_cnty_assign[Assign == 1]$BA_Code)
  v.diff <- setdiff(v.ba, v.ba_assign)
  if (length(v.diff) > 0){
    sf.ba_cnty_assign <- sf.ba_cnty_assign %>%
      .[,Rule3 := ifelse(max(BA_Share, na.rm= TRUE) == BA_Share,
                         1,
                         0),
        by = "BA_Code"] %>%
      .[(BA_Code %in% v.diff) & Rule3 == 1, Assign := 1]
  }
  
  #####
  ### Check 2: Check that all counties are assigned for all years
  #####
  dt.fips <- as.data.table(fips_codes) %>%
    .[,c("state", "state_code", "state_name", "county_code")] %>%
    .[,county_code := str_c(state_code, county_code)] %>%
    setnames(c("Abbv_st", "FIPS_st", "Name_st", "FIPS_cnty")) %>%
    unique()
  
  v.fips <- unique(sf.county$FIPS_cnty)
  v.fips_assign <- unique(sf.ba_cnty_assign[Assign == 1]$FIPS_cnty)
  dt.diff <- setdiff(v.fips, v.fips_assign) %>%
    as.data.table() %>%
    setnames("FIPS_cnty") %>%
    merge(dt.fips,
          by = "FIPS_cnty",
          all.x = TRUE)
  
  #####
  ### Write merged data to file
  #####
  
  ### Assign counties to BA and write assignment crosswalk
  sf.ba_cnty_assign <- sf.ba_cnty_assign %>%
    .[Assign == 1] %>%
    .[!(`BA_Code` == "NYIS" & (FIPS_st != 36))] %>%
    .[!(`BA_Code` == "ISNE" & (FIPS_st == 36))] %>%
    .[!(`BA_Code` == "MISO" & (FIPS_cnty == "20167"))] %>%
    .[,c("FIPS_cnty", "Region_Name", "BA_Code")]
  
  ### Creating VEA/CISO directly due to issues w/ shapefile
  sf.vea_add = data.table("FIPS_cnty" = c("32023", "32009"),
                          "Region_Name" = c("California", "California"),
                          "BA_Code" = c("CISO", "CISO"))
  
  sf.ba_cnty_assign <- rbindlist(list(sf.ba_cnty_assign, sf.vea_add)) %>%
    .[,Year := i.year]
  return(sf.ba_cnty_assign)
}
out.dt <- map(v.years.sm, f_ba_make) %>% rbindlist()

### Write results to file
fwrite(out.dt,
       here("outputs", "crosswalks", "EIA_BA-County.csv"))
