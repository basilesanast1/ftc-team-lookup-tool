# FTC Team Lookup

A terminal tool for looking up FIRST Tech Challenge (FTC) teams. It shows team details, awards by season, a full award history, and a summary of a team's events and awards. It uses the official FIRST Tech Challenge Events API.

This project is not affiliated with or endorsed by FIRST.

## Features

- **Look up a team:** name, school, location, rookie year, and website for a chosen season, plus that season's awards with the event for each.
- **Team summary:** number of awards per season and total events participated.
- **Full award list:** every award a team has won across all seasons since its rookie year, with the season and event for each.
- **Season selection:** view any season, not just the current one.
- **Saved credentials:** enter your API key once, and the tool stores it locally.

## Requirements

- Python 3.10 or newer
- An FTC Events API account (free)

## Getting an API key

1. Go to https://ftc-events.firstinspires.org/services/API
2. Register and request an API key. You'll receive a username and token.

## Installation

```bash
git clone https://github.com/your-username/ftc-team-lookup.git
cd ftc-team-lookup
pip install -r requirements.txt
```

## Usage

```bash
python ftc_lookup.py
```

On the first run, the program asks for your API username and token and saves them to `ftc_credentials.json` in the same folder as the script. You can change them later from the menu.

### Menu

```
1  Look up a team
2  Team summary
3  Full award list
4  Change season
5  Update credentials
6  Quit
```

## Credentials

Your credentials are stored in `ftc_credentials.json`. The program creates this file on first run. On systems that support it, the file is set so only your user account can read it.

The file stores your token in plain text. Don't share it, and don't commit it to version control. The `.gitignore` in this repository already excludes it.

## Notes

- The API sometimes returns 502, 503, or 504 errors. The tool retries these automatically.
- Some teams have no awards for a season. The tool shows "none" for those seasons instead of an error.
- Team short names come directly from the API, and a few teams have unusual values in that field.
- The team summary makes one request per season, so it can take a few seconds for teams with long histories.

## Project structure

```
ftc-team-lookup/
├── ftc_lookup.py
├── ftc_credentials.example.json
├── requirements.txt
├── LICENSE
├── .gitignore
└── README.md
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
