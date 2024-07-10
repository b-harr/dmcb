# Scrape Links - Spotrac

library(dplyr)
library(rvest)
library(XML)
library(stringr)
library(janitor)

# Set Spotrac Team IDs
spotrac_link_ids <- c("atlanta-hawks", "brooklyn-nets", "boston-celtics", "charlotte-hornets", "cleveland-cavaliers", "chicago-bulls", "dallas-mavericks", "denver-nuggets", "detroit-pistons", "golden-state-warriors", "houston-rockets", "indiana-pacers", "la-clippers", "los-angeles-lakers", "memphis-grizzlies", "miami-heat", "milwaukee-bucks", "minnesota-timberwolves", "new-york-knicks", "new-orleans-pelicans", "oklahoma-city-thunder", "orlando-magic", "philadelphia-76ers", "phoenix-suns", "portland-trail-blazers", "san-antonio-spurs", "sacramento-kings", "toronto-raptors", "utah-jazz", "washington-wizards")
years <- c(2024:2027)
links <- paste0("https://www.spotrac.com/nba/", spotrac_link_ids, "/cap/_/year/")
spotrac_links <- {}
n <- 0

for(i in 1:length(years)){
  for(j in 1:length(links)){
    n <- n + 1
    spotrac_links[n] <- paste0(links[j], years[i], "/")
  }
}

# Create Function to Scrape Links
scrape_spotrac_links <- function(link){
  webpage <- read_html(link)
  player_links <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[1]/a') %>% 
    html_attr("href")
  players <- webpage %>%
    html_nodes(xpath = '//*[@id="table_active"]/tbody//td[1]/a') %>% 
    html_text()
  tibble <- html_table(webpage)[[1]]
  player_df <- data.frame(
    "SpotracName" = players,
    "SpotracUrl" = player_links
  )
  player_df <- player_df %>%
    filter(player_df$SpotracName != "")
  player_df <- data.frame(
      "SpotracName" = player_df$SpotracName,
      "SpotracUrl" = player_df$SpotracUrl,
      "SpotracSalary" = tibble$`Cap Hit`,
      "SpotracNotes" = "",
      "SpotracSource" = link,
      "SpotracSeason" = paste0(str_sub(link, -5, -2), "-", as.integer(str_sub(link, -5, -2))-2000+1),
      "SpotracClean" = make_clean_names(str_replace_all(str_to_lower(player_df$SpotracName), "\\.", ""))
    )
  return(player_df)
}

spotrac_data <- {}

for(i in 1:length(spotrac_links)){
  data <- scrape_spotrac_links(spotrac_links[i])
  spotrac_data[i] <- list(data)
}

spotrac_data_df <- do.call("rbind", spotrac_data)
spotrac_data_df <- spotrac_data_df[order(spotrac_data_df$SpotracName, spotrac_data_df$SpotracSeason),]

write.csv(spotrac_data_df, "../data/Spotrac.csv", row.names = F)