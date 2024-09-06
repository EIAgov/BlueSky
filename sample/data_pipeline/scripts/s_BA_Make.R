############################################################################
### s_BA_Make.R: Load and clean raw BA shapefile from OES
###
### Description: This script loads reference tables for the EIA-930 survey
###              data and renames/cleans these tables for use in filtering
###              Balancing Authority (BA) and Balancing Authority Subregion
###              (BASR) operating data. Then, it loads our internal BA
###              shapefile and fixes any invalid geometries before saving
###              as a gpkg file collection.
### - Inputs
###   * EIA930_Reference_Tables.xlsx
###   * EIA_BalanceAuthority_2023.shp
### - Outputs
###   * EIA_BA_Details.csv
###   * EIA_BA.gpkg
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

### Check if directories are constructed prior to creation
v.dir <- c("crosswalks", "shapefiles")
f.dirs <- function(i.str.dirname){
  str.dirloc <- here("outputs", i.str.dirname)
  if (!dir.exists(str.dirloc)){
    dir.create(str.dirloc, recursive = TRUE)
  }
}
invisible(map(v.dir, f.dirs))


################################################################################
### Step 1: Load EIA 930 BA Descriptions
################################################################################

### Set coordinate reference system for all spatial data
v.crs  <- "ESRI:102008"

#####
### Loading reference tables for EIA930 Data; Balancing Authority Table
###   - Rename variable names
###   - Filter out generational only BA's
###   - Filter for BAs still active after 2018
#####
iso_ba.dt <- read_excel(here("inputs", "EIA930", "EIA930_Reference_Tables.xlsx"),
                        sheet = "BAs") %>%
  as.data.table() %>%
  setnames(c("BA Code", "BA Name", "Region/Country Name", "Demand by BA Subregion", 
             "Active BA", "Activation Date", "Retirement Date"),
           c("BA_Code", "BA_Name", "Region_Name", "Demand_by_BASR",
             "BA_Active", "BA_ActiveDate", "BA_RetireDate")) %>%
  .[`Generation Only BA` == "No"] %>%
  .[`U.S. BA` == "Yes"] %>%
  .[is.na(mdy(BA_RetireDate)) | (mdy(BA_RetireDate) > mdy("12/31/2018"))] %>%
  .[,c("BA_Code", "BA_Name", "Region_Name", "Demand_by_BASR",
       "BA_Active", "BA_ActiveDate", "BA_RetireDate")]

### Write cleaned BA details as a separate file
fwrite(iso_ba.dt,
       here("outputs", "crosswalks", "EIA_BA_Details.csv"))

################################################################################
### Step 2: Load and clean BA and BASR shapefiles from file
################################################################################

#####
### Note: Load the Balance Authority Shapefiles
###   - Rename BA_Code
###   - Join reference tables to shapefile
###   - Transform shapefile into new CRS and fix geometry
#####
sf.ba     <- st_read(here("inputs", "shapefiles", "EIA_BalanceAuthority_2023.shp")) %>%
  rename(BA_Code = EIAacron) %>%
  .[,c("BA_Code", "geometry")] %>%
  left_join(iso_ba.dt,
            by = "BA_Code") %>%
  filter(!is.na(Region_Name)) %>%
  st_transform(v.crs) %>%
  st_make_valid() %>%
  st_buffer(dist = 0) # Stupid valid geometry tricks

### Save shapefile for BA file
st_write(sf.ba,
         here("outputs", "shapefiles", "EIA_BA.gpkg"),
         layer = "BA",
         delete_dsn = TRUE)

