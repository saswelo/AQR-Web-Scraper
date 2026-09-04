# AQR Landing Page (website) Scrape Bot

This repository contains two sripts that implement the process of scraping landing pages of ER (Expert Raters) AQR evals:

- **prepare_raw_data.ipynb:** Loads two spreadsheet files, one of them containing AQR evals content (query, ad title, landing page) and the other individual ER raters ratings to evals that have been audited by SERs. This script pairs evals content with their type of ad (Shopping or Text ad), ER agreement rate with the SER rating, and a binary flag indicating whether a majority of the ERs agree with the SER rating.

- **lp_scrapper.ipynb:** Loads a spreadsheet file (produced by the **prepare_raw_data.ipynb** script), takes each of the evals' landing page URL and scrapes their website content as text.

## Dependencies
Run the following command to install the dependencies needed to run both scripts:

```conda create --name <env> --file requirements.txt```