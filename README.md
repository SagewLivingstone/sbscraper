# Rainbow Six Siege - Scoreboard Scraper

## Note: This project was abandoned partway on 9/29/2020 for the following reasons:
* It was discovered that at certain aspect ratios (pretty much everything but 16:9), the text chat covers the scoreboard, leaving the algorithm unusable
* Azure's OCR algorithm is unable to accurately differentiate text frorm icons they are right next to
  * e.g. an operator icon next to the player name is sometimes read as text instead of an icon
  * [jager_icon] name is read as: "IIL" + "<some portion of the player's name>"
  

## Purpose

This library is used to extract player names and statistics from a screenshot of a rainbow six siege scoreboard. It uses Azure's OCR service to detect the text and a simple rolling-set algorithm to detect columns and rows in the scoreboard table. This dramatically decreases the time to enter player stats at the end of a comp match.

**Usage:**

`python service.py <SCREENSHOT_URL>`

_no longer under development_
