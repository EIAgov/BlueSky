############################################################################
### s_BA-ISD_Join.R: Station locations to regions -- Spatial Join
###
### Description: This script assigns stations from the NOAA-Integrated
###             Surface Dataset (ISD) to counties based on distance to the
###             county centroid in order to merge weather data to counties.
###             The script finds the *n_stations* closest stations to the
###             county centroid and returns those station IDs plus their distance
###             to the county centroid.
###
### - Inputs
###   * isd-history_loc.txt
###   * EIA_BA-BASR-County.csv
### - Outputs
###   * NOAA_ISD_Stations.csv
###   * EIA_County-ISD.csv
###
### Date Commented: 7/9/24
############################################################################

#####
### Set-up: Loading packages (included in Conda environment)
#####
libraries <- c("tidyverse", "data.table", "tigris", "sf", "readxl", "here")
invisible(lapply(libraries, library, character.only = TRUE))

### Ensure working directory pointed at Snakefile location
here::i_am("Snakefile")

### Snakemake Inputs
v.years.sm <- snakemake@params$years_sm
v.n_stations.sm <- snakemake@params$n_stations
#v.years.sm <- 2018:2022
#v.n_stations.sm <- 10

### Check if directories are constructed prior to creation
v.dir <- c("noaa")
f.dirs <- function(i.str.dirname){
  str.dirloc <- here("outputs", i.str.dirname)
  if (!dir.exists(str.dirloc)){
    dir.create(str.dirloc)
  }
}
invisible(map(v.dir, f.dirs))
################################################################################
### Note: Load and clean weather data
################################################################################

### Set CRS
v.crs   <- "ESRI:102008"

### Point to location where ISD directory located (e.g. html)
isd.loc <- readLines(here("inputs", "noaa", "isd-history_loc.txt"))

### Delete previous station files
file.remove(list.files(path = here("outputs",
                                   "noaa"),
                       pattern = "NOAA_ISD_Stations",
                       full.names = TRUE))
#####
### Note: Read fixed width file
###   - Filter for US only
###   - Rename variables
###   - Filter for active stations
#####
dt.station <- read_fwf(file = isd.loc,
                       skip = 22,
                       fwf_cols(USAF = c(1, 7), WBAN = c(8, 13),
                                station_name = c(14,43),
                                CTRY = c(44,48),
                                ST   = c(49, 51),
                                CALL = c(52, 57),
                                LAT  = c(58, 65),
                                LON  = c(66, 74),
                                ELEV = c(75, 82),
                                BEGIN = c(83, 91),
                                END  = c(92, 100))) %>%
  as.data.table()                                   %>%
  .[CTRY == "US"]                                   %>%
  .[!is.na(LAT) & !is.na(LON)]                      %>%
  .[LAT != 0 & LON != 0]                            %>%
  .[,station_id := str_c(USAF, WBAN)]                %>%
  .[,date_start := ymd(BEGIN)]                      %>%
  .[,date_end   := ymd(END)]                        %>%
  .[date_end >= dmy("01/01/2015")]                  %>%
  .[,date_dl := lubridate::now()]                   %>%
  .[,c("station_id", "station_name", "date_start",
        "date_end", "date_dl", "USAF", "WBAN", "CTRY", "ST", "CALL",
        "LAT", "LON", "ELEV")]

### Write to file
fwrite(dt.station,
       here("outputs", "noaa", paste0("NOAA_ISD_Stations.csv")))

### Note: Create sf from data
sf.station <- st_as_sf(dt.station[,c("station_id", "date_start", "date_end", "LAT", "LON")],
                       coords = c("LON", "LAT"),
                       crs    = 4326) %>%
  st_transform(.,
               crs = v.crs)

################################################################################
### Load Crosswalk and Merge to County Spatial Data
################################################################################

### Load BA-BASR File
dt.ba_basr <- fread(here("outputs", "crosswalks", "EIA_BA-BASR-County.csv")) %>%
  .[,FIPS_cnty := str_pad(FIPS_cnty, side = "left", pad = "0", width=5)]

#####
### Create function for calculating distances and finding nearest station
#####
f_findnearest_year <- function(i.year){
  
  ### Load county shapefile for each year; calculate centroid
  sf.county = tigris::counties(cb = TRUE,
                               year = i.year)  %>%
    st_transform(v.crs)                        %>%
    mutate(FIPS_cnty    = GEOID)               %>%
    dplyr::select(FIPS_cnty)                   %>%
    filter(FIPS_cnty %in% dt.ba_basr$FIPS_cnty) %>%
    st_centroid()
  
  #####
  ### Create function that, for each county, finds nearest stations
  #####
  f_findnearest <- function(i,
                            i2.year = i.year,
                            i.n_stations = v.n_stations.sm,
                            i.sf.county = sf.county,
                            i.sf.station = sf.station){
    
    ### Calculate distance to centroids
    dist.v <- as.numeric(st_distance(i.sf.station, i.sf.county[i,]))/1000
    
    ### Create data table and sort by distance
    dt <- data.table("station_id" = i.sf.station$station_id,
                     "date_start" = i.sf.station$date_start,
                     "date_end"   = i.sf.station$date_end,
                     "distance_km" = dist.v) %>%
      setorder(distance_km) %>%
      .[,FIPS_cnty := i.sf.county[i,]$FIPS_cnty]
    
    ### Create output dataset with n_station number of stations for county
    dt_y <- copy(dt[date_start <= mdy(paste0("01/01/", i2.year)) & 
                    date_end >= mdy(paste0("12/31/", i2.year))]) %>%
      .[1:i.n_stations] %>%
      .[,Year := i2.year] %>%
      .[,!c("Date_Start", "Date_End")]
    return(dt_y)
  }
  dt.int_year = rbindlist(map(1:dim(sf.county)[1], f_findnearest))
}
dt.int <- map(v.years.sm, f_findnearest_year) %>% rbindlist()
  
### Merge intersected counties to station dataset
dt.int_m <- merge(dt.int,
                  dt.station[,c("station_id", "USAF", "WBAN", "LAT", "LON",
                                "station_name")],
                  by = c("station_id"))


dt.ba_basr_isd <- merge(dt.ba_basr,
                        dt.int_m,
                        by = c("Year", "FIPS_cnty"),
                        all.x = TRUE,
                        allow.cartesian = TRUE) %>%
  .[,c("FIPS_cnty", "Year", "station_id", "distance_km")] %>%
  unique() %>%
  setorder(FIPS_cnty, distance_km, Year)

### Save county-ba-basr-isd walk
fwrite(dt.ba_basr_isd,
       here("outputs", "crosswalks", "EIA_County-ISD.csv"))
