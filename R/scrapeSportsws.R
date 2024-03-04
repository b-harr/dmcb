library(rvest)
library(XML)
library(dplyr)
library(stringr)
library(janitor)

link <- "https://sports.ws/nba/stats"
webpage <- read_html(link)

players <- webpage %>%
  html_nodes(xpath = "//td[1]//a") %>%
  html_text()
links <- webpage %>%
  html_nodes(xpath = "//td[1]//a") %>%
  html_attr("href")
names <- webpage %>%
  html_nodes(xpath = "//td[1]") %>%
  html_text()

positions <- data.frame(players, links, names)
sportsws <- trimws(str_split_fixed(names, ",", 3))
df <- data.frame("SportswsId" = positions$links, "SportswsShortName" = sportsws[,1], "SportswsTeam" = sportsws[,2], "SportswsPosition" = sportsws[,3], "SportswsUrl" = paste0("https://sports.ws",positions$links))
df1 <- df[!duplicated(df[c("SportswsId")]),] %>%
  filter(!(SportswsId == "/nba/-"))
cleanname <- make_clean_names(str_replace_all(df1$SportswsId, "/nba/", ""))
df2 <- data.frame(df1, "SportswsClean" = cleanname)
df2 <- df2[order(df2$SportswsId),]

write.csv(df2, "../data/Sportsws.csv", row.names = F)