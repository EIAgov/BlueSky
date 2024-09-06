############################################################################
### s_BA-BASR_Merge.R: Merging together the BA and BASR crosswalks
###
### Description: All inputs from previous steps pulled together, merged and
###              uploaded to a geopackage containing BAs, BASRs, and county
###              assignments
###              
### - Inputs
###   * EIA_BA-County.csv
###   * EIA_BASR-County.csv
###   * EIA_BA.gpkg
###   * EIA_BASR.gpkg
### - Outputs
###   * EIA_BA-BASR-County.csv
###   * BA-BASR_Merge.gpkg
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

### Snakemake Inputs
v.years.sm <- snakemake@params$years_sm
#v.years.sm <- 2018:2022

################################################################################
### Read in all crosswalks and shapefiles
################################################################################

v.crs  <- "ESRI:102008"
### Load County Crosswalks
dt.ba_cw     <- fread(here("outputs", "crosswalks", "EIA_BA-County.csv")) %>%
  .[,FIPS_cnty := str_pad(FIPS_cnty, width = 5, side = "left", pad = "0")]
dt.basr_cw   <- fread(here("outputs", "crosswalks", "EIA_BASR-County.csv")) %>%
  .[,FIPS_cnty := str_pad(FIPS_cnty, width = 5, side = "left", pad = "0")]

### Load shapefiles
sf.ba <- st_read(here("outputs", "shapefiles", "EIA_BA.gpkg"),
                      layer = "BA")
sf.basr <- st_read(here("outputs", "shapefiles", "EIA_BASR.gpkg"),
                   layer = "BASR")

################################################################################
### Write gpkg file w/ layers for county assignments and original maps
################################################################################

### Create County Maps and merge crosswalks to county
dt.ba_basr_merge <- copy(dt.ba_cw) %>%
  .[,BASR_Code := NA_character_] %>%
  .[!(BA_Code %in% unique(dt.basr_cw$BA_Code))] %>%
  .[,FIPS_st := str_sub(FIPS_cnty, end = 2)] %>%
  rbind(dt.basr_cw, fill = TRUE) %>%
  .[,BA_BASR_Code := str_c(BA_Code, "-", ifelse(is.na(BASR_Code),
                                                "NA",
                                                BASR_Code))] %>%
  setorder(FIPS_cnty, BA_Code)

## Write merged BA and BASR files together into one
fwrite(dt.ba_basr_merge,
       here("outputs", "crosswalks", "EIA_BA-BASR-County.csv"))

### Merge BA-BASR crosswalk to county shapefile for each year
f_countymerge <- function(i.year){
  
  ### Load County File and calculate area
  sf.cnty <- tigris::counties(cb = TRUE,
                              year = i.year) %>%
    st_transform(v.crs) %>%
    mutate(FIPS_cnty = GEOID) %>%
    mutate(Area_m2  = as.numeric(round(st_area(.),0))) %>%
    select(FIPS_cnty, Area_m2)
  
  ### Merge data from ba-basr to county file for the year
  sf.ba_basr_merge <- copy(sf.cnty) %>%
    inner_join(dt.ba_basr_merge[Year == i.year],
               by = "FIPS_cnty") %>%
    select(-Area_m2)
  return(sf.ba_basr_merge)
}
sf.ba_basr_merge_full <- map(v.years.sm, f_countymerge) %>% bind_rows()

### Write all data to file by layer name
st_write(sf.ba,
         here("outputs", "shapefiles", "BA-BASR_Merge.gpkg"),
         layer = "BA",
         delete_dsn = TRUE)
st_write(sf.basr,
         here("outputs", "shapefiles", "BA-BASR_Merge.gpkg"),
         layer = "BASR",
         delete_layer = TRUE)
st_write(sf.ba_basr_merge_full,
         here("outputs", "shapefiles", "BA-BASR_Merge.gpkg"),
         layer = "County",
         delete_layer = TRUE)
