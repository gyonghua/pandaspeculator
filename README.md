# About
__A project to showcase skills acquired after web development self study from May - Aug 2017.__  

This is a forex alert system made with Flask. It does the following:  
- scan major currency pairs for multiple bar patterns on the 1 hour, 4 hour, 1 day and sends subscribers telegram alerts when they occur. 
- sends subscribers a daily email report of notable stop clusters present in the currency market

# Implementation
## Notable libraries
- Semantic UI
- Peewee
- Requests
- flask-mail
- flask-wtf
- flask-restful
## Modules
### Telegram webhook
An endpoint that acts as a webhook to the Telegram bot which handles user authentication on the Telegram app. This portion is needed as Telegram requires user to first contact the bot before the bot can send messages to the user.
### User management system
UI for users to:  
- register
- manage subscriptions which includes
  - option to choose which service to subscribe to
  - option to choose which currency pairs to subscribe to 
- interface for admin to manage users
### Cron job scripts
Alerts and email reports are executed using cron jobs  
## Security
Password storage are handled using salted hash.  
Flask-wtf and wtforms are used to handle forms and protection again XSRF.

# Project Takeaways
The current implementation is suitable for small user bases. To scale, the cron jobs should be reimplemented using pub/sub or as a queue system.  
  
Logging was not implemented in this project and it is sorely missed after deployment as I'm forever wondering if I'm missing out on anything that is occurring in the apps.  
  
The impact of the lack of unit tests is not notable in this project as most features are easily tested manually. But its presence will definitely be appreciated on larger projects. 
  
Both logging and unit testing are high on my to learn list.
