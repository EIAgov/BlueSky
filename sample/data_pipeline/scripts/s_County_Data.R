############################################################################
### Demand Profiles -- County-Level Data Collection
### Description: This file collects county level population estimates from a
###              a variety of sources to append to system shapes database for 
###              purposes of aggregating weather up to 
### Date: 12-27-23
############################################################################

#####
### Load Libraries (This should work w/ snakemake Conda)
#####
libraries <- c("tidyverse", "data.table", "tigris", "sf", "readxl", "tidycensus", "here")
invisible(lapply(libraries, library, character.only = TRUE))
here::i_am("Snakefile")

### Load Snakemake inputs
v.years_sm <- snakemake@params$years_sm
v.census_key <- snakemake@params$cen_key_sm
#v.years_sm <- 2018:2022


### Install census api key
sm.key = v.census_key
tryCatch({
  census_api_key(sm.key)
  readRenviron("~/.Renviron")
}, warning = function(w) {
  print("Census key install issued warning; check for any issues")
}, error = function(e) {
  print("Error installing census key; might already exist (try overwrite)")
}
)

### Create output directories if they don't exist
v.dir <- c("census")
f.dirs <- function(i.str.dirname){
  str.dirloc <- here("outputs", i.str.dirname)
  if (!dir.exists(str.dirloc)){
    dir.create(str.dirloc)
  }
}
invisible(map(v.dir, f.dirs))

##### 
### Load 2023 population estimates
#####
dt.fips <- fips_codes %>% as.data.table()
f_newpop <- function(i.year, i.st){
  dt = tryCatch(expr = {
    pop.dt <- get_acs(
      state = i.st,
      geography = "county",
      variables = "B01001_001",
      year = i.year
    )
    
    ### Output population data only
    dt <- data.table("FIPS_cnty" = pop.dt$GEOID,
                     "population" = pop.dt$estimate,
                     "year" = i.year)
  },
  error = function(e){
    ### Output population data only
    dt <- data.table("FIPS_cnty" = character(),
                     "population" = numeric(),
                     "year" = numeric())
    return(dt)

  })
}
grid.inp <- expand.grid(v.years_sm, unique(dt.fips$state))
dt.pop  <- map2(grid.inp[,1], grid.inp[,2], f_newpop) %>% rbindlist()

if (!dir.exists(here("outputs", "census"))){
  dir.create(here("outputs", "census"), recursive = TRUE)
}
fwrite(dt.pop,
       here("outputs", "census", paste0("County_Population.csv")))
