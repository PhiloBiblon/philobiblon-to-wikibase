# Configure QuickStatements for pbuidev

Updated QuickStatements server with new features added in upstream version and not included yet in QuickStatements Wikibase Cloud:

- Force create new statements for same values: https://github.com/magnusmanske/quickstatements/pull/35
- Define Julian dates: https://github.com/magnusmanske/quickstatements/pull/36

## Installation

Assumptions:
- Our external url for QuickStatements is: http://qs.philobiblon.duckdns.org:9191
	
Steps:	
1. Register OAuth consumer on wikibase to use along QuickStatements.
	1. Request new consumer:
		1. Go to wikibase -> `Special pages` -> `OAuth consumer registration` -> `Request a token for a new consumer`
		2. Fill the form and propose new consumer:
			- Application name: `QuickStatements`
			- Consumer version: `1.0`
			- OAuth protocol version: `OAuth 1.0a`
			- Applicable project:	`All projects on this site`
			- OAuth "callback URL": http://qs.philobiblon.duckdns.org:9191/api.php
			- Allow consumer to specify a callback in requests and use "callback" URL above as a required prefix: `Yes`
			- Applicable grants:
				- `High-volume editing`
				- `Edit existing pages`
				- `Edit protected pages`
				- `Create, edit, and move pages`
			- Accept conditions
	2. Approve previous consumer:
		1. Go to wikibase -> `Special pages` -> `Manage OAuth consumers` -> `Queue of proposed consumer requests`
		2. Select our consumer -> `review/manage` -> `Select Approved` -> `Update consumer status`

2 - Open port 9191 in your router to allow external callback.

3 - Start docker.
```
docker-compose up -d
```
