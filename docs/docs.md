# AzureKitty official documentation
This file is meant to reference any useful information that users or developers could need.

## Installation
Install PowerShell and the following modules (`Install-Module <module-name>`):
- ExchangeOnlineManagement
- Microsoft.Graph
- MicrosoftTeams
- Microsoft.Online.SharePoint.PowerShell
- Az
- AzureAD

One-liner:
```PS
Install-Module ExchangeOnlineManagement, Microsoft.Graph, MicrosoftTeams, Microsoft.Online.SharePoint.PowerShell, Az, AzureAD
```

Create a virtualenv and install the required modules:
`python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

## Graph API Application Setup
- Go to Azure Active Directory in the left navigation pane on the Azure Admin Panel.
- Once opened, navigate to Application Registrations.
- Select New registration and name it.
- Set the type of account to be supported under Account in this organizational directory only.
- Leave the Redirect URI empty.
- Validate the registration.
- On the overview page, copy the Application ID and Directory ID.
- Under Manage, choose Authentication > Advanced settings, then set Allow public client flows to Yes, and then Save.

## Contribution
You're welcome to contribute to this project, as long as the tests work. If necessary, add new tests.
