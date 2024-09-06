############################################################################
### s_BASR_Make.R: Load and clean raw BASR shapefile from OES
###
### Description: This script loads reference tables for the EIA-930 survey
###              data and renames/cleans these tables for use in filtering
###              Balancing Authority (BA) and Balancing Authority Subregion
###              (BASR) operating data. To aggregate BASRs and create geographies
###              where we do not have data, we recode certain BASRs into new
###              codes. We write this crosswalk to file.
###
###              Then, the script loads our internal BASR shapefile and fixes 
###              any invalid geometries before reclassifying and cleaning 
###              to make the shapefile consistent with the EIA930 codes. 
###              The recoded data tables are merged to the shapefile and are
###              saved as a gpkg file collection.
###              
### - Inputs
###   * EIA930_Reference_Tables.xlsx
###   * RTO_Regions.shp
### - Outputs
###   * EIA_BASR-Details.csv
###   * EIA_BASR.gpkg
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
    dir.create(str.dirloc)
  }
}
invisible(map(v.dir, f.dirs))

################################################################################
### Step 1: Load EIA 930 BASR Descriptions
################################################################################

#####
### Loading reference tables for EIA930 Data; BASR Table
###   - Rename variable names
###   - Filter for BAs still active after 2018
#####
iso_sr.dt <- read_excel(here("inputs", "EIA930", "EIA930_Reference_Tables.xlsx"),
                        sheet = "BA Subregions") %>%
  as.data.table() %>%
  setnames(c("BA Code", "BA Name", "BA Subregion Code", "BA Subregion Name", 
             "Active Subregion", "Activation Date", "Retirement Date"),
           c("BA_Code", "BA_Name", "BASR_Original", "BASR_Name",
             "BASR_Active", "BASR_ActiveDate", "BASR_RetireDate")) %>%
  .[is.na(mdy(BASR_RetireDate)) | (mdy(BASR_RetireDate) > mdy("12/31/2018"))]

#####
### Creating matrix of recoded BASR assignments
#####
swpp_sr.dt <- matrix(c("CSWS", "SSW",
                       "EDE", "CEN",
                       "OKGE", "SSW",
                       "SPS", "SSW",
                       "GRDA", "SSW",
                       "INDN", "CEN",
                       "KACY", "CEN",
                       "KCPL", "CEN",
                       "LES", "UPPR",
                       "MPS", "CEN",
                       "NPPD", "UPPR",
                       "OKGE", "SSW",
                       "OPPD", "UPPR",
                       "SECI", "CEN",
                       "SPRM", "CEN",
                       "SPS", "SSW",
                       "WAUE", "UPPR",
                       "WFEC", "SSW",
                       "WR", "CEN",
                       "ZONA", "ZONA",
                       "ZONB", "ZNBC",
                       "ZONC", "ZNBC",
                       "ZOND", "ZNDF",
                       "ZONE", "ZNDF",
                       "ZONF", "ZNDF",
                       "ZONG", "ZNGI",
                       "ZONH", "ZNGI",
                       "ZONI", "ZNGI",
                       "ZONJ", "ZONJ",
                       "ZONK", "ZONK",
                       "VEA", "SCEV",
                       "SCE", "SCEV"),
                     ncol  = 2,
                     byrow = TRUE) %>%
  as.data.table() %>%
  setnames(c("BASR_Original",
             "BASR_Code"))

### Merge reclassifications to the subregions dataset; write to crosswalks
iso_sr.dt <- iso_sr.dt %>%
  merge(swpp_sr.dt,
        by = "BASR_Original",
        all.x = TRUE) %>%
  .[is.na(BASR_Code), BASR_Code := `BASR_Original`]

### Write crosswalk to file
fwrite(iso_sr.dt,
       here("outputs", "crosswalks", "EIA_BASR-Details.csv"))

################################################################################
### Step 2: Load EIA 930 BASR Shapefile and Reclassify to Cohere w/ 930
################################################################################

#####
### Note: Load the BASR Shapefiles
###   - Transform shapefile into new CRS and fix geometry
###   - Convert to data table and filter for BASRs in EIA930
###   - Join cleaned/filtered BASR data table to shapefile
#####

v.crs  <- "ESRI:102008"
sf.basr <- st_read(here("inputs", "shapefiles", "RTO_Regions.shp")) %>%
  st_transform(crs = v.crs) %>%
  st_make_valid(.)
dt.basr <- as.data.table(sf.basr) %>%
  .[,!c("geometry")] %>%
  .[!(NAME %in% c("MISO_North", "MISO_South"))] %>%
  .[!(RTO_ISO == "ERCOT" & str_detect(LOC_NAME, "LZ_"))] %>%
  .[LOC_TYPE != "HUB"] %>%
  .[RTO_ISO != "SPP"] %>%
  .[!(RTO_ISO == "CAISO" & LOC_TYPE == "ZON")]
sf.basr <- inner_join(sf.basr[,c("Unique_ID", "geometry")],
                      dt.basr,
                      by = "Unique_ID")

#####
### Recoding basr to align with RTO Shapefile where possible
#####
v.iso1 <- c("CAISO", "ISONE", "NYISO", "MISO", "PJM", "ERCOT")
v.iso2 <- c("CISO", "ISNE", "NYIS", "MISO", "PJM", "ERCO")
dt.sf.basr_recode <- dt.basr[,c("Unique_ID", "RTO_ISO", "LOC_ABBREV", "LOC_NAME")] %>%
  .[RTO_ISO == "ISONE", LOC_ABBREV := LOC_NAME] %>%
  .[RTO_ISO == "MISO", LOC_ABBREV := str_pad(str_replace_all(LOC_ABBREV,
                                                             "LRZ",
                                                             ""),
                                             width = 4,
                                             side = "left",
                                             pad = "0")] %>%
  .[RTO_ISO == "MISO" & (LOC_ABBREV %in% c("0002", "0007")),LOC_ABBREV := "0027"] %>%
  .[RTO_ISO == "MISO" & (LOC_ABBREV %in% c("0003", "0005")),LOC_ABBREV := "0035"] %>%
  .[RTO_ISO == "MISO" & (LOC_ABBREV %in% c("0008", "0009", "0010")),LOC_ABBREV := "8910"] %>%
  .[.(RTO_ISO = v.iso1, to = v.iso2), on = "RTO_ISO", RTO_ISO := i.to] %>%
  setnames(c("Unique_ID", "BA_Code", "LOC_ABBREV", "BASR_Original"))
v.sf.basr_recode <- c("CISO", "PGE", "PGAE",
                      "NYIS", "West", "ZONA",
                      "NYIS", "Genessee", "ZONB",
                      "NYIS", "Central", "ZONC",
                      "NYIS", "North", "ZOND",
                      "NYIS", "Mohawk Val", "ZONE",
                      "NYIS", "Capital", "ZONF",
                      "NYIS", "Hud Val", "ZONG",
                      "NYIS", "Milwood", "ZONH",
                      "NYIS", "Dunwoodie", "ZONI",
                      "NYIS", "NYC", "ZONJ",
                      "NYIS", "Long Is", "ZONK",
                      "PJM", "AECO", "AE",
                      "PJM", "APS", "AP",
                      "PJM", "BGE", "BC",
                      "PJM", "ComEd", "CE",
                      "PJM", "DAYTON", "DAY",
                      "PJM", "JCPL", "JC",
                      "PJM", "METED", "ME",
                      "PJM", "PECO", "PE",
                      "PJM", "PEPCO", "PEP",
                      "PJM", "PPL", "PL",
                      "PJM", "PENELEC", "PN",
                      "PJM", "PSEG", "PS",
                      "ERCO", "Southern", "SOUT",
                      "ERCO", "Far_West", "FWES",
                      "ERCO", "West", "WEST",
                      "ERCO", "North_C", "NCEN",
                      "ERCO", "North", "NRTH",
                      "ERCO", "East", "EAST",
                      "ERCO", "South_C", "SCEN",
                      "ERCO", "Coast", "COAS")
dt.sf.basr_recode_fix <- as.data.table(matrix(data = v.sf.basr_recode,
                                              ncol = 3,
                                              byrow = TRUE)) %>%
  setnames(c("BA_Code", "LOC_ABBREV", "BASR_Original"))
dt.sf.basr_recode <- merge(dt.sf.basr_recode, dt.sf.basr_recode_fix,
                           by = c("BA_Code", "LOC_ABBREV"),
                           all.x = TRUE,
                           suffixes = c("", ".fill")) %>%
  .[is.na(BASR_Original.fill), BASR_Original := LOC_ABBREV] %>%
  .[!is.na(BASR_Original.fill), BASR_Original := BASR_Original.fill] %>%
  .[,!c("BASR_Original.fill")] %>%
  merge(iso_sr.dt[,c("BASR_Original", "BASR_Code", "BA_Code")],
        by = c("BASR_Original", "BA_Code"),
        all.x = TRUE) %>%
  .[,!c("LOC_ABBREV")]

#####
### Merge reclassifications to the shapefile
#####

sf.basr_merge <- copy(sf.basr)[,c("Unique_ID", "geometry")] %>%
  left_join(dt.sf.basr_recode,
            by = "Unique_ID") %>%
  filter(!is.na(BASR_Code))

### Write to File
st_write(sf.basr_merge,
         here("outputs", "shapefiles", "EIA_BASR.gpkg"),
         layer = "BASR",
         delete_dsn = TRUE)
