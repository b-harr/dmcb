# Load libraries
library(dplyr)
library(rvest)
library(XML)
library(stringr)
library(janitor)

# Set links to scrape
spotrac_link_ids <- c("atlanta-hawks", "brooklyn-nets", "boston-celtics", "charlotte-hornets", "cleveland-cavaliers", "chicago-bulls", "dallas-mavericks", "denver-nuggets", "detroit-pistons", "golden-state-warriors", "houston-rockets", "indiana-pacers", "la-clippers", "los-angeles-lakers", "memphis-grizzlies", "miami-heat", "milwaukee-bucks", "minnesota-timberwolves", "new-york-knicks", "new-orleans-pelicans", "oklahoma-city-thunder", "orlando-magic", "philadelphia-76ers", "phoenix-suns", "portland-trail-blazers", "san-antonio-spurs", "sacramento-kings", "toronto-raptors", "utah-jazz", "washington-wizards")
years <- c(2024:2028)
links <- paste0("https://www.spotrac.com/nba/", spotrac_link_ids, "/cap/_/year/")
spotrac_links <- vector()

n <- 0
for(i in 1:length(years)){
  for(j in 1:length(links)){
    n <- n + 1
    spotrac_links[n] <- paste0(links[j], years[i], "/")
  }
}

# Function to clean text
clean_text <- function(text){
  text_clean <- gsub(" ", "", gsub("\n", "", text))
  return(text_clean)
}

# Function to scrape data from Spotrac links
scrape_spotrac_links <- function(link){
  webpage <- read_html(link)
  
  player <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[1]/a') %>% 
    html_text()
  # If no players found, return empty data frame
  if (length(player) == 0) {
    return(data.frame())
  }
  # Clean and filter data
  player <- player[player != ""]
  player_clean <- make_clean_names(tolower(gsub("\\.", "", player)))
  
  player_link <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[1]/a') %>% 
    html_attr("href")
  # Filter invalid links
  player_link <- player_link[player_link != "javascript:void(0)"]
  
  position <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[2]') %>% 
    html_text() %>%
    clean_text()
  
  age <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[3]') %>% 
    html_text() %>%
    clean_text()
  
  type <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[4]') %>% 
    html_text() %>%
    clean_text()
  
  cap_hit <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[5]') %>% 
    html_text() %>%
    clean_text()
  
  # Build season and create data frame
  season <- paste0(str_sub(link, -5, -2), "-", as.integer(str_sub(link, -5, -2))-2000+1)
  contracts <- data.frame(player, player_link, season, cap_hit, position, age, type, link, player_clean)
  # Create new column without suffixes like _sr, _jr, _ii, _iii, _iv
  contracts <- contracts %>%
    mutate(player_clean_no_suffix = gsub("_(sr|jr|ii|iii|iv|v|vi|vii)$", "", player_clean))
  # Exclude "Two-Way" contracts
  contracts <- contracts %>% 
    filter(cap_hit != "Two-Way") %>%
    filter(cap_hit != "-")
  
  return(contracts)
}

# Scrape data from all links
spotrac_data <- list()

for(i in 1:length(spotrac_links)){
  data <- scrape_spotrac_links(spotrac_links[i])
  spotrac_data <- append(spotrac_data, list(data))
}

# Combine all data into one data frame and order by player and season
spotrac_data_df <- do.call("rbind", spotrac_data)
spotrac_data_df <- spotrac_data_df[order(spotrac_data_df$player, spotrac_data_df$season),]

# Save to CSV
write.csv(spotrac_data_df, "../data/Spotrac.csv", row.names = F)
