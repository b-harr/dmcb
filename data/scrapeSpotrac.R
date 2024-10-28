# Load necessary libraries
library(dplyr)       # For data manipulation
library(rvest)       # For web scraping
library(stringr)     # For string manipulation
library(janitor)     # For cleaning column names

# Define team IDs for constructing Spotrac URLs
teams <- c(
  "atlanta-hawks", "brooklyn-nets", "boston-celtics", "charlotte-hornets",
  "cleveland-cavaliers", "chicago-bulls", "dallas-mavericks", "denver-nuggets",
  "detroit-pistons", "golden-state-warriors", "houston-rockets", "indiana-pacers",
  "la-clippers", "los-angeles-lakers", "memphis-grizzlies", "miami-heat",
  "milwaukee-bucks", "minnesota-timberwolves", "new-york-knicks",
  "new-orleans-pelicans", "oklahoma-city-thunder", "orlando-magic",
  "philadelphia-76ers", "phoenix-suns", "portland-trail-blazers",
  "san-antonio-spurs", "sacramento-kings", "toronto-raptors",
  "utah-jazz", "washington-wizards"
)
years <- c(2024:2028)  # Define the range of seasons to scrape

# Construct Spotrac URLs for each team and season
links <- paste0("https://www.spotrac.com/nba/", teams, "/cap/_/year/")
spotrac_links <- vector()

n <- 0
for (i in 1:length(years)) {
  for (j in 1:length(links)) {
    n <- n + 1
    spotrac_links[n] <- paste0(links[j], years[i], "/")
  }
}

# Define a helper function to remove unnecessary whitespace and newline characters
clean_text <- function(text) {
  text_clean <- gsub(" ", "", gsub("\\n", "", text))
  return(text_clean)
}

# Define the main function to scrape player contract data from a given Spotrac URL
scrape_spotrac_links <- function(link) {
  webpage <- read_html(link)
  
  # Extract player names; if no players found, return an empty data frame
  player <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[1]/a') %>% 
    html_text()
  if (length(player) == 0) {
    return(data.frame())
  }
  player <- player[player != ""]  # Remove any blank player entries
  player_clean <- make_clean_names(gsub("\\.", "", tolower(player)))  # Clean player names
  
  # Extract player profile links, positions, ages, contract types, and cap hits
  player_link <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[1]/a') %>% 
    html_attr("href")
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
  
  # Construct the season in "YYYY-YY" format, e.g., "2024-25"
  season_year <- as.integer(str_sub(link, -5, -2))
  season <- paste0(season_year, "-", substr(season_year + 1, 3, 4))
  
  # Combine the extracted data into a data frame
  contracts <- data.frame(player, player_link, season, cap_hit, position, age, type, link, player_clean)
  
  # Remove suffixes like _sr, _jr, _ii from player names for cleaner data comparison
  contracts <- contracts %>%
    mutate(player_clean_no_suffix = gsub("_(sr|jr|ii|iii|iv|v|vi|vii)$", "", player_clean))
  
  # Filter out unwanted entries such as "Two-Way" contracts or missing cap hits
  contracts <- contracts %>% 
    filter(cap_hit != "Two-Way") %>%
    filter(cap_hit != "-")
  
  return(contracts)
}

# Scrape data from all constructed URLs
spotrac_data <- list()
for (i in 1:length(spotrac_links)) {
  data <- scrape_spotrac_links(spotrac_links[i])
  spotrac_data <- append(spotrac_data, list(data))
}

# Combine all scraped data into a single data frame and sort it by player and season
spotrac_data_df <- do.call("rbind", spotrac_data)
spotrac_data_df <- spotrac_data_df[order(spotrac_data_df$player, spotrac_data_df$season),]

# Save the cleaned and organized data to a CSV file
write.csv(spotrac_data_df, "../data/Spotrac.csv", row.names = FALSE)
