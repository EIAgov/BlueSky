############################################################################
### s_BASR-County_Join.R: Load and clean raw BASR shapefile from OES
###
### Description: This script loads and joins together the BASR shapefile and 
###              yearly county shapefiles, assigning counties to BASRs until 
###              all counties that are assigned a BA (in the contiguous 48 states)
###              with BASRs also have a BASR assigned to them. This is done
###              via the f_basr_make function below for each year fed to this 
###              script from snakemake. This is run for each year to deal with
###              changes in county definitions over time (e.g. Connecticut).
###              After the intersection, we correct based on state boundaries
###
###              To fix a handful of issues with this merge, we use a previous
###              hand-constructed version of the BASR to county crosswalk and
###              merge this to the spatially joined county-BASR data table.
###              
### - Inputs
###   * EIA_BA-County.csv
###   * EIA_BA-SubregionToCounty.csv
###   * EIA_BASR-Details.csv
###   * EIA_BASR.gpkg
### - Outputs
###   * EIA_BASR-County.csv
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
### Load necessary shapefiles and details data
################################################################################

### Balancing Authority Subregions
sf.basr <- st_read(here("outputs", "shapefiles", "EIA_BASR.gpkg"),
                   layer = "BASR")
dt.basr_detail <- fread(here("outputs", "crosswalks", "EIA_BASR-Details.csv"))
dt.ba_cw <- fread(here("outputs", "crosswalks", "EIA_BA-County.csv")) %>%
  .[,FIPS_cnty := str_pad(FIPS_cnty, width = 5, side = "left", pad = "0")]

################################################################################
### For each county assigned to a BASR-BA, assign each county to subregion
################################################################################

v.basr_avail <- c("ERCO", "CISO", "PJM", "ISNE", "NYIS", "MISO", "SWPP")
v.crs  <- "ESRI:102008"

#####
### Create function for spatial join and run for snakemake-defined years
#####
f_basr_make <- function(i.year){
  
  ### Load Counties (from API), set CRS, and calculate county size
  sf.ba_cnty  <- tigris::counties(cb = TRUE,
                                 year = i.year)  %>%
    st_transform(v.crs)                        %>%
    mutate(FIPS_cnty = GEOID)                  %>%
    mutate(Area_m2  = as.numeric(round(st_area(.),0))) %>%
    select(FIPS_cnty, Area_m2) %>%
    inner_join(dt.ba_cw[(BA_Code %in% v.basr_avail) & Year == i.year],
               by = "FIPS_cnty")
  
  ################################################################################
  ### Note: Intersect BASR boundaries w/ counties
  ### Assignment Rules:
  #   - if >50% overlap, assign to BA
  #   - if multiple overlap, assign all majority overlapping BAs
  #   - if no BA assignment, assign to largest
  #   - if BA goes unassigned, assign to county w/ largest
  ################################################################################
  sf.basr_cnty <- st_intersection(sf.ba_cnty, sf.basr) %>%
    mutate(area_int = st_area(.)) %>%
    mutate(BASR_Share = round(as.numeric(area_int/Area_m2),3))
  dt.basr_cnty <- as.data.table(sf.basr_cnty) %>%
    .[BA_Code == BA_Code.1] %>%
    .[,!c("geometry")] %>%
    .[,Rule1 := ifelse(BASR_Share > 0.5,
                       1,
                       0)] %>%
    .[,NoRule1 := ifelse(max(Rule1, na.rm = TRUE)==1,
                         0,
                         1),
      by = "FIPS_cnty"] %>%
    .[,Rule2 := ifelse(max(BASR_Share, na.rm= TRUE) == BASR_Share,
                       1,
                       0),
      by = "FIPS_cnty"] %>%
    .[,NoRule2 := ifelse((Rule1 == 0 & Rule2 == 0),
                         1,
                         0)] %>%
    .[,Assign := ifelse((Rule1 == 1) | (Rule1 == 0 & Rule2 == 1),
                        1,
                        0)] %>%
    .[Assign == 1] %>%
    .[,c("FIPS_cnty", "BA_Code", "BASR_Code")]
  
  #####
  ### Fix missing assignments, first w/ state based classifications, then w/ 
  ### specific classifications to ensure all counties assigned to BA have BASR tag
  #####
  dt.basr_cnty_fix <- left_join(sf.ba_cnty, dt.basr_cnty,
                                by = c("FIPS_cnty", "BA_Code"))   %>%
    as.data.table() %>%
    .[,!c("geometry")] %>%
    .[,FIPS_st := str_sub(FIPS_cnty, end = 2)] %>%
    .[,Index := seq(.N)] %>%
    .[`BA_Code` == "SWPP" & (FIPS_st == "35" | FIPS_st == "48" | FIPS_st == "40" | FIPS_st == "05" | FIPS_st == "22"),
      `BASR_Code` := "SSW"] %>%
    .[`BA_Code` == "SWPP" & (FIPS_st == "08" | FIPS_st == "20" | FIPS_st == "29"),
      `BASR_Code` := "CEN"] %>%
    .[`BA_Code` == "SWPP" & (FIPS_st == "30" | FIPS_st == "38" | FIPS_st == "46" | FIPS_st == "27" | FIPS_st == "19"),
      `BASR_Code` := "UPPR"] %>%
    .[`BA_Code` == "SWPP" & (FIPS_st == "31"),
      `BASR_Code` := "UPPR"]  %>%
    .[is.na(`BASR_Code`) & `BA_Code` == "MISO" & (FIPS_st == "05" | FIPS_st == "22" | FIPS_st == "28" | FIPS_st == "48"), 
      `BASR_Code` := "8910"] %>%
    .[is.na(`BASR_Code`) & `BA_Code` == "MISO" & (FIPS_st == "19" | FIPS_st == "29"), 
      `BASR_Code` := "0035"] %>%
    .[is.na(`BASR_Code`) & `BA_Code` == "MISO" & (FIPS_st == "27" | FIPS_st == "46" | FIPS_st == "38" | FIPS_st == "30"), 
      `BASR_Code` := "0001"] %>%
    .[is.na(`BASR_Code`) & `BA_Code` == "MISO" & (FIPS_st == "21" | FIPS_st == "18"), 
      `BASR_Code` := "0006"] %>%
    .[is.na(`BASR_Code`) & `BA_Code` == "MISO" & (FIPS_st == "17"), 
      `BASR_Code` := "0004"] %>%
    .[is.na(`BASR_Code`) & `BA_Code` == "PJM" & (FIPS_st == "18"),
      `BASR_Code` := "AEP"] %>%
    .[is.na(`BASR_Code`) & `BA_Code` == "PJM" & (FIPS_st == "26"),
      `BASR_Code` := "AEP"] %>%
    .[is.na(`BASR_Code`) & `BA_Code` == "PJM" & (FIPS_st == "37"),
      `BASR_Code` := "DOM"]
  
  ### Note: Specific corrections (from a previous attempt)
  dt.basr_corrections <- fread(here("inputs", "shapefiles", "EIA_BA-SubregionToCounty.csv")) %>%
    .[,`BA_Code` := unlist(lapply(MATCH, function(x) str_sub(x,
                                                             end = str_locate(x,
                                                                              "_")[1,1]-1)))] %>%
    .[,`BASR_Code` := unlist(lapply(MATCH, function(x) str_sub(x,
                                                               start = str_locate(x,
                                                                                  "_")[1,1]+1)))] %>%
    .[`BA_Code` == "MISO", `BASR_Code` := str_pad(BASR_Code,
                                                  4,
                                                  "left",
                                                  "0")]  %>%
    .[,FIPS_cnty := str_c(str_pad(STATEFP, 2, side = "left", pad = "0"),
                          str_pad(COUNTYFP, 3, side = "left", pad = "0"))] %>%
    .[,.(FIPS_cnty, BASR_Code, BA_Code)]
  
  ### Merge hand corrected counties w/ intersections
  dt.basr_cnty_na <- dt.basr_cnty_fix[is.na(BASR_Code)] %>%
    .[,!c("BASR_Code")] %>%
    merge(dt.basr_corrections,
          all.x = TRUE,
          by = c("FIPS_cnty", "BA_Code"))
  
  ### Merge together all assignments into single file; drop unassigned
  dt.basr_cnty_full <- rbind(dt.basr_cnty_fix[!(Index %in% dt.basr_cnty_na$Index)], dt.basr_cnty_na) %>%
    .[!is.na(BASR_Code)] %>%
    .[,!c("Area_m2", "Index")] %>%
    .[,Year := i.year]
  return(dt.basr_cnty_full)
}
dt.out <- map(v.years.sm, f_basr_make) %>% rbindlist()

### Write out BASR-County Crosswalks
fwrite(dt.out,
       here("outputs", "crosswalks", "EIA_BASR-County.csv"))
