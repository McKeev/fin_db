# **fin_db**:  My Personal Financial Database

*Technology used: Python, PostgreSQL, Docker, Bash Scripts, Linux*

This project is a financial database (750+ instruments) hosted on my Raspberry Pi.
I developed this to ensure data quality and availability for future projects (faster, more predictable queries).
The system features:

- Daily market data ingestions (self refreshing) for equities, ETFs and currencies.
- A containerised environment, allowing for easy portability and reproducibility.
- Daily backups using pgBackRest.
- Enhanced API pulling: batching, retries, and validation.
- A complete and scalable SQL schema (indices, views, internal IDs).
- Support for multiple sources through source prioritisation.
- A modular design allowing for future expansions.

## Skills developped during this project

- [Data Engineering](#data-engineering-)
- [DevOps](#devops-)
- [Operational Automation](#operational-automation-)
- [API Integration](#api-integration-)

### Data Engineering [🔗](/db/README.md)

This was the main skill developped during this project.
From what to store, to how to store it; there were a lot of questions that needed answering.
This was my first time creating a relational database from scratch and I had a lot to learn.
I opted to keep the following as my guiding principle:

> **<center> Always store data in its rawest form possible. </center>**

For example, I do not store adjusted close as it is a derived field.
I instead retrieve raw closing prices (in original currency) and total returns, which allow me to construct adjusted closes if needed.
I also did my best to keep this project simple and efficient which is the reason I limited the fields I ingest in favour of more instruments.
I used LSEG (refinitiv) to bootstrap my data and I use Yahoo Finance (their recent data is okay but older datapoints are not great) for [daily ingest jobs](scripts/daily_ingest.py). 

For more information (including my [schema](db/schema.dbml)), I invite you to look through `/db` (excluding `/db/ops`) where you'll find my migrations and others.

### DevOps [🔗](/db/ops/README.md)

I wanted the database to run in a Docker container so it could be easily moved and deployed to other machines.
Docker allows me to avoid environment issues and ensures I can run this project on a wider variety of systems.
For example, the main database runs on a Raspberry Pi (Linux-Debian) but I also run a copy-test environment locally on my mac.
It would simply be a matter of pulling the git repo, downloading my google drive backup and starting a new container.
This portability also helps with reproducibility and facilitates testing!

The biggest challenged I faced in this respect was integrating **pgBackRest** (backup system) into the setup.
Running this with a dockerised postgres is a notorious bane and my solution was to implement my own image.
I also faced a lot of permission issues and to ensure I wouldn't have to fix them repetitively, I set up easy bash scripts.

In the end, it was worth it!
My database backs up daily and syncs with Google Drive, allowing for easy restores if (when 😅) I make mistakes.

### Operational Automation [🔗](/scripts/daily_ingest.py)

To ensure I don't have to manually ingest data, I had to develop robust automations.
These are run frequently using cron jobs (a linux feature that allows for scheduling tasks).
Accordingly, I do not check the outputs of these jobs regularly and instead rely on my system.
I guarantee that my scripts don't crash unexpectedly by having catches for potential fails.
To protect against potential silent issues, I developed the system to communicate issues and feedback to me via Telegram, which I can view on my phone.

### API Integration [🔗](/src/fin_db/providers/)

To facilitate work with outside sources, I developed wrappers around existing APIs and libraries.
These serve to ensure I don't hit usage/rate limits and create easier functions to obtain data.
Furthemore, they also help provide basic verififications which ensure consistent outputs.


