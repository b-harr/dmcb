import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

from utils.spotrac_scraper import scrape_players


PLAYER_URLS = [
    "https://www.spotrac.com/nba/player/_/id/23600/deaaron-fox",
    "https://www.spotrac.com/nba/player/_/id/70653/devin-vassell",
    "https://www.spotrac.com/nba/player/_/id/31588/keldon-johnson",
    "https://www.spotrac.com/nba/player/_/id/82196/victor-wembanyama",
    "https://www.spotrac.com/nba/player/_/id/78268/julian-champagnie",
    "https://www.spotrac.com/nba/player/_/id/8070/tobias-harris",
    "https://www.spotrac.com/nba/player/_/id/98598/dylan-harper",
    "https://www.spotrac.com/nba/player/_/id/23670/luke-kornet",
    "https://www.spotrac.com/nba/player/_/id/91750/stephon-castle",
    "https://www.spotrac.com/nba/player/_/id/10815/harrison-barnes",
    "https://www.spotrac.com/nba/player/_/id/98614/carter-bryant",
    "https://www.spotrac.com/nba/player/_/id/107936/jayden-quaintance",
    "https://www.spotrac.com/nba/player/_/id/107959/tarris-reed-jr",
    "https://www.spotrac.com/nba/player/_/id/27975/jordan-mclaughlin",
    "https://www.spotrac.com/nba/player/_/id/100548/david-jones-garcia",
    "https://www.spotrac.com/nba/player/_/id/108433/jakobi-gillespie",
    "https://www.spotrac.com/nba/player/_/id/108559/maliq-brown",
    "https://www.spotrac.com/nba/player/_/id/80015/jon-elmore",
    "https://www.spotrac.com/nba/player/_/id/100565/rj-davis",
    "https://www.spotrac.com/nba/player/_/id/99267/taelon-peter",
    "https://www.spotrac.com/nba/player/_/id/90227/malik-williams",
    "https://www.spotrac.com/nba/player/_/id/75746/lindy-waters-iii",
    "https://www.spotrac.com/nba/player/_/id/13335/mason-plumlee",
    "https://www.spotrac.com/nba/player/_/id/8057/bismack-biyombo",
    "https://www.spotrac.com/nba/player/_/id/13326/kelly-olynyk",
]


def main():
    contract_details = scrape_players(PLAYER_URLS)
    print(contract_details)


if __name__ == "__main__":
    main()
