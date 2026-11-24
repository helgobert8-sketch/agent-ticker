> ## Documentation Index
> Fetch the complete documentation index at: https://docs.devin.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Recent Updates

> The latest Devin updates: recently released features, improvements, and bug fixes across the product, updated with each release.

**November 23, 2026**

## Sessions & Workspace

### Open a session side by side

Option/Alt+click a session link to open it in a split pane.

### Session search moves to the command palette

Search sessions with Cmd/Ctrl+K; the inline search in the Sessions sidebar is removed.

## Security

### Code scan cancellations in audit logs

Audit logs record who cancelled a code scan, from the web app or the v3 API.

## Enterprise & Settings

### Warning before deleting secrets used by Preflight checks

Before you delete an org secret, the Secrets page lists the automations whose Preflight checks use it.

## Integrations & MCPs

### Offer marketplace plugins to members

Admins can mark a marketplace plugin as Offered to members instead of Required.

### Allow an MCP tool for the whole session

MCP tool approval cards add Allow for this session.

### API-key MCP headers bound to secrets

Blank headers on API-key marketplace MCP servers are bound to secrets, and unused secrets are flagged.

### Custom MCP servers default to Automatic authentication

New custom MCP servers start with Automatic authentication selected.

## Automations

### Run automations from the right-click menu

Right-click a row on the Automations list for Run now, Open in new tab and Copy link.

**November 20, 2026**

### Introducing Access and Sharing

The access changes below are rolling out gradually and are off by default. Contact your Cognition representative to enable them for your enterprise.

#### Repositories & Environments

##### SCM access mismatch checker

Admins get a report of repos where access in Devin is different from access in GitHub or GitLab. Admins can also turn on repo sync, which adds the repos you have in GitHub or GitLab to your repo picker. Repos your org already added stay.

##### Shareable environments available

All users by default will be able to create an environment once and use it in any org. Admins will be able to remove this permission from the default member role. You only see environments whose repos you have access to. Existing environments are unchanged.

#### Sharing

##### Share with user groups

Settings has a User groups page where you create groups and add members. Wherever Manage access is available (secrets, environments, sessions, automations, plugins, playbooks, skills, MCP servers, knowledge), you can pick a user group as well as individual people or the org.

##### Per-session sharing

Each session has its own sharing setting: just you, one or more user groups, your org or account-wide. Sessions that use a repo, secret or environment shared only with you or your group start as just you, with a warning before you widen it. Admins can set the org default.

##### Slack session sharing change

Sessions started from Slack still reply in the channel, but only people the session is shared with can give it instructions. When someone else replies, Devin offers a one-click way to share the session with them.

##### Granularly shareable secrets

When adding or editing a secret in an org, you can share it with a user group. By default it is shared with the org, as today.

##### Plugins, playbooks, skills, MCP servers and knowledge

Each can be shared with a user group instead of the whole org, including MCP servers that do not use OAuth.

#### Automations & Service Users

##### Automations

Automations also receive more granular permissions and can be shared with a user group. Sessions they start use the same sharing.

##### Service users and bots

Service users and shared bots use only the repos and resources explicitly given to them; repo sync does not apply.

#### Devin Review

##### Review shows only your repos

In an org, Review lists only repos and PRs you can access, including SCM mirrored access.

#### DeepWiki & Ask

##### DeepWiki and Ask use your repos

DeepWiki and Ask answer from the repos you can access, including SCM mirrored access.

### Sessions & Workspace

**Paste videos into session chat**

Paste a video into the session chat composer to attach it, the same way you paste images.

**More search options in the session IDE**

The IDE's Search view adds match case, whole word and regex options, replace and replace all, and files to include or exclude.

**Citations open at the cited lines**

Clicking a citation in Devin's message opens the file on the exact lines it cites.

**Typo-tolerant settings search**

Settings search and the command palette now find results even when a letter is missing.

**Recent repositories first in repo pickers**

The composer's repository picker and the @-mention repository list show your recently used repositories first.

### Security

**Triaged state for findings**

Security findings gain a Triaged state and tab, for findings someone has looked at but not resolved yet.

**Summary cards and reviewer counts on PR reviews**

Security > PR reviews adds summary cards and a Findings filter, and the reviewers card shows how many findings each reviewer found, fixed and dismissed.

**Set a finding's assignee through the API and MCP**

A new API endpoint and MCP tool set or clear the assignee of a code scan finding.

### Enterprise & Settings

**Disable a plugin at a scope**

In Settings > Customize, admins can disable a plugin for their organization or enterprise without uninstalling it.

**Convert a shared outpost pool without draining it**

Converting a shared outpost pool to account-wide no longer requires draining its organizations first.

### Integrations & MCPs

**Sazabi plugin**

The Sazabi plugin is now in the plugin marketplace.

**Several installations of an API-key plugin MCP**

An API-key plugin MCP can have another installation at personal, organization or enterprise scope.

**Skills in the v3 Sessions API**

The v3 Sessions API returns the skills each session used.

### Slack & Microsoft Teams

**Slack sender shown on watched thread replies**

Replies in a watched Slack thread show in the session transcript under the sender's Slack name.

**November 19, 2026**

### Introducing Devin Bots

[Devin Bots](https://devin.ai/bots) are always-on Devins with their own identity, memory and permissions. Give a Bot a goal and it keeps doing the job: it breaks the work down, runs Devin sessions in parallel, each on its own cloud machine, and keeps each one going until the pull request is ready to merge. You set the direction and steer when it matters.

Message your Bots in the web app or on Slack, text or call them, or add them to a group chat. Start from a template, such as a QA engineer, code reviewer or on-call engineer, or describe the outcome you want.

### Sessions & Workspace

**Share Ask threads from the sidebar on mobile**

On mobile, Ask thread rows in the sidebar now have a Share action that opens the device share sheet.

**Copy link for Ask threads in the sidebar**

Ask thread rows in the sidebar now have a Copy link action.

**Typing outside a text box no longer enters the composer**

Characters typed while no input is focused, such as after clicking in the transcript, are no longer inserted into the session or new-session composer; click the composer to type.

**Session header shows "Syncing" while a session catches up**

When you open a session, its header shows an animated "Syncing" label next to the title until the session has caught up with the server.

**Plugin edits show as a plugin card in sessions**

When Devin edits a plugin without needing an approval card (a pre-approved personal plugin or a Security plugin), the session transcript now shows the saved plugin card with what the edit changed and a link to the plugin.

**Quote attachments in chat from their tab**

Attachment tabs in a session now have a "Quote in chat" button that adds the document to your message, and inline attachment cards keep a single Copy menu.

**Artifact publishing names who will see it**

Before you publish an artifact, the share dialog now says that anyone in your organization (named) will be able to view the page, and shows a warning when the session itself is private.

### Devin Review

**Charge a repository's Reviews to an organization or budget**

Repository billing rules in Review settings (Billing tab) let admins pick a repository and charge its Reviews, including Review chat, to an organization or budget instead of the PR author, manual launch or grant; organization Review managers can set rules for the repositories they manage.

**Turn the Review list reading pane on or off**

The Review list's reading pane beside the PR list can now be switched off, so clicking a row opens the pull request's full page instead; the choice is saved per account.

**Show a stacked PR's merge target as its branch name**

In Devin Review, the merge-target chip for a stacked PR can be switched between showing the target PR and its branch name, and the choice is remembered.

**Before image shown for renamed image files**

Devin Review's diff viewer now shows the Before image for image files a PR renames.

### Security

**Security sidebar groups less-used pages under More**

The Security sidebar now moves less-used pages into a More menu, and you can pin a page to the sidebar or unpin it.

**Findings gains a By repository tab**

On the Security Findings page, a new By repository tab lists each repository with its open findings count and last scan time, replacing the separate Security > Repositories page.

**Link code-scan findings to an existing session via API**

The v3 API and the devin\_code\_scan\_manage MCP tool can now link one or more code-scan findings to an existing Devin session you own.

**Validation screenshots shown inline on findings**

On a Security finding's detail page, image artifacts from the finding's validation are now shown inline instead of only as file links.

**Choose base branch and PR grouping in Fix with Devin**

Fix with Devin on code scan findings now always opens a dialog where you can set a base branch (default: repository default) and, for 2+ security-scan findings, choose one PR per root cause, one per finding, or one for all findings.

**See running and failed validations on code scan findings**

The code scan finding detail sheet now shows when a finding's validation is running ("Validating") or failed without a result ("Validation failed"), with a link to the validation session and the previous result.

**Validate with Devin from a finding's detail view**

The finding detail action bar in Security scans now has a Validate with Devin button for findings that can be validated.

### Integrations & MCPs

**MCPs list redesigned with an Installed group and search**

In Settings > Customize > MCPs, the MCP catalog now uses plugin-style rows, groups your installed MCPs under Installed above Available, and moves search into the header.

**Confirm before discarding unsaved MCP setup changes**

MCP setup sheets and editors (including enterprise MCP server settings) now ask for confirmation before closing or navigating away would discard unsaved input.

**Customize shows organization- or enterprise-level installs**

In Settings > Customize, plugins and MCPs that come from your organization or enterprise now say which level they are installed at.

**MCP approval cards say what Always allow covers**

The MCP tool approval card in sessions now names the tool and whether Always allow applies to all your sessions or everyone in the organization, and the resolved row shows Always allowed with a Change link.

**Plugin sheet notes MCPs you already installed separately**

A plugin's sheet now tells you when its MCP is already installed on its own, explains that installing the plugin keeps it, and links to View MCP.

**Warning when an MCP sign-in is shared organization-wide**

Signing in to an MCP installed for an organization or enterprise now warns that the sign-in and credentials are shared with everyone who can use it and suggests a service account.

**Choose the Entra tenant for Azure DevOps**

In Settings > Integrations > Azure DevOps, org admins whose Microsoft account belongs to more than one Entra tenant can now choose which tenant to connect.

**Switched-off MCP installations show as Disabled**

In Customize (MCPs list and plugin details), an MCP installation that is signed in but switched off now reads "Disabled" without the green dot, and is no longer counted in the "N connected" summaries.

**Marketplace hides MCPs replaced by native integrations**

The MCP marketplace and MCP suggestions no longer offer servers such as Slack, Linear, GitLab or Pylon that a native integration or marketplace plugin replaces.

**Security notice before each additional plugin MCP connection**

Adding another installation of a plugin's MCP server in Settings > Customize now shows the plugin security notice before it connects.

### Automations & Oncall

**Oncall user group mention triggers can match thread replies**

Oncall responders with a Slack user group mention trigger can add an "is thread reply" condition so mentions of the group inside threads also start a run.

**November 18, 2026**

### Sessions & Workspace

**Choose who a new session is shared with**

The home composer has a **Shared with** picker that shows who a new session will be visible to (you, your organization or your enterprise, per your organization's sharing settings) and lets you keep it to only you before it starts.

**Start sessions as Only you**

A new toggle in Settings > Preferences, **Start sessions as Only you**, keeps the sessions you start from the composer hidden from everyone else unless you share them.

**Private sessions don't post to Slack**

Picking **Only you** for a new session on the home composer detaches any Slack channel and turns off the Slack toggle, with a note that Slack is unavailable for private sessions.

**Confirm before making a hidden session visible**

**Make visible to team** on a hidden session now asks for confirmation and names who will gain access, and an organization-wide MCP install card in a private session warns that every member gets the server.

**Warnings before a private session's results reach more people**

In a private session, approval cards for knowledge, playbooks, schedules, automations and shared plugins warn who else will see the result, and widening a session's General access in the Share dialog asks for confirmation.

**Attachments follow session visibility**

An organization attachment linked to sessions can now be opened only by people who can read one of those sessions, in the web app and the API.

**Attach a long message as a file**

Sending a message that is too long now asks first and offers to attach its quoted text, or the whole prompt, as a Markdown file.

**Zoom in the image viewer**

The full-screen image viewer has zoom in and out buttons; Cmd/Ctrl + and - zoom the image and Cmd/Ctrl 0 fits it, instead of zooming the page.

**Repeated pushes show as one worklog row**

In the session worklog, repeated pushes of the same commit to the same branch within five minutes show as one **Pushed branch** row.

### Devin Review

**Update branch from Devin Review**

When a GitHub pull request is behind its base and you can update it, Devin Review's merge button becomes **Update branch**, which asks GitHub to update the branch.

### Security

**Source column in the Security findings table**

The Security findings table has an optional **Source** column (turn it on from the column picker) showing where each finding came from: a scan, a connection import, a red team or a pull request review.

**Chat about selected findings**

When you select findings on the Security findings page, the selection bar has a **Chat** button that opens the findings chat.

### Enterprise & Settings

**Search a security profile's allowed domains**

Org admins can search the allowed domain list when editing a security profile, by domain or label.

### Integrations & MCPs

**See which Google account an MCP connection uses**

MCP connections signed in with a Google account show the address they are signed in as, in Customize > MCPs, on MCP cards in the session, and in the API.

**Personal or shared access on MCP installations**

In Customize > MCPs, an organization's or enterprise's MCP installation says whether it uses **Personal access** (each member signs in) or **Shared access**.

**Choose where an MCP installation goes**

In Customize, a plugin MCP's button reads **Add installation to** the layer it adds to, with an **Add somewhere else** option (including yourself), and each installation says who it is installed for.

**DevinDash MCP is out of beta**

The DevinDash MCP in the MCP marketplace is no longer marked beta.

### Slack & Microsoft Teams

**Replies from people without session access in Slack threads**

When someone without access to a session replies in a Slack thread the session watches, the session shows their message under their name, notes that Devin wasn't shown it, and links to it in Slack.

**Devin can delete its own Slack messages**

Devin can now delete Slack messages its own session posted, and it can read Slack canvases.

**Devin can edit its Microsoft Teams direct messages**

In Microsoft Teams, Devin can edit a direct message it sent, replacing its text and card.

**Teams channel mentions open the channel**

Microsoft Teams channel mentions in session messages and the composer show as #channel chips that open the channel in Teams.

**November 17, 2026**

### Sessions & Workspace

**Simpler people search when sharing a session**

The session Share dialog now has an always-open people search field, and it warns you when the session runs on a standalone environment.

**Search Apps from Cmd+K**

The command palette (Cmd+K) now searches your Apps, showing each result's thumbnail, description and status, with scope chips and an option to create an App from your search.

### Devin Review

**Security gets its own tab in Review settings**

Review settings now have a separate **Security** tab for vulnerability and security-hardening suggestions (Settings > Review > Security).

**Devin Review status on Azure DevOps pull requests**

Organizations that post Devin Review checks now also get a Devin Review status on Azure DevOps pull requests, attached to the pull request's latest iteration.

**Org-scoped Review settings for enterprise orgs**

Enterprise admins can open Review settings for a single organization in the enterprise; enterprise-level controls show there as read-only.

**Custom reviewers: search repositories across organizations**

When creating a custom reviewer, admins can search repositories across all of their member organizations.

### Security

**Impact summaries on pull request findings**

Findings from pull request security reviews can now include a short impact summary that explains the risk to someone who hasn't seen the code.

**Code scans Overview counts link to their findings**

On the Code scans Overview, the open and merged PR counts and the new, dismissed and resolved findings counts now open the matching findings.

**Linked code scan findings in embedded reviews**

Wherever a pull request's embedded review opens, it now shows the code scan findings linked to that pull request.

### Slack & Microsoft Teams

**Richer Slack posts from Devin**

Devin can now post images, rich text, tables, charts, cards and carousels in Slack.

**November 16, 2026**

### Sessions & Workspace

**Subscribers and Mark done**

Your sidebar now shows the sessions you are subscribed to. Mark done replaces Archive: it moves a session to your Done folder while it keeps running and stays in the sidebars of its other subscribers, so you can clear your sidebar without stopping work others depend on.

**Phonebook: one identity across your connected services**

Devin now keeps a phonebook of each member's linked identities across Devin, Slack, Microsoft Teams, your git providers, Jira, Linear and Pylon. Devin has a tool to match a person to their connected identities, and it tags people by those linked identities: a mention in Devin now tags the person in Devin and in Slack at the same time.

**Slack channel picker in the composer**

Type # in any cloud session composer to pick a Slack channel.

**Session event search matches words separately**

Searching a session's events now matches each word on its own, so a query finds events that contain the words in any order.

### Security

**CSV export of Security Findings**

Export the Security Findings table to CSV.

**Configure is now Customize**

Security > Configure is renamed Customize. Manage security-profile plugins there, let a profile's skills set scan paths and include/exclude globs, pick the repositories a threat-model rule applies to, and keep skills and rules writable when shared uploads are off.

**Findings polish**

The browser tab is named after the open finding, severity is spelled out in the finding title, and the finding sheet crossfades between findings.

### Enterprise & Settings

**Enterprise Knowledge managers maintain migrated skills**

Enterprise Knowledge managers can read and maintain skills migrated from Knowledge.

**Skills layers page in Customize**

Customize > Skills has a page listing the layers you can write skills to, and malformed plugin content says what is wrong in the catalog.

### Slack & Microsoft Teams

**Tagging Devin in an old Slack thread starts a new session**

When Devin is tagged in a Slack thread whose session is too old to resume, it starts a new session instead of failing. !ultrafast is accepted as an alias of !fastultra in Slack and Teams.

**Mentions on Teams and in quotes**

On Microsoft Teams, @user mentions are written back as native mentions. The quote of a user's message names the mentioned person, and message headers name Slack or Teams.

**November 13, 2026**

**German UI Language**

Deutsch can now be selected as the display language in Preferences, using the terms engineers use for session, merge, push, prompt, logs, service user and secrets.

**Session File Editor Saves on Cmd/Ctrl+S**

The session file editor no longer saves automatically: press Cmd/Ctrl+S to save, a dot on the tab marks unsaved files, a cloud icon in the editor header confirms each save to Devin's machine, and closing a tab or leaving a session with unsaved edits asks first. Devin is told which files you saved so it can take your edits into account.

**Sidebar Filter Menu Simplified**

The sessions sidebar Filter menu no longer has the Machine type and Skill filters; both remain available on the Sessions page. The session title menu now lists the sessions above the current session's parent.

**Artifacts Rail Beside the Chat**

Workspace tabs no longer open on their own as Devin works. What a session produces — pull requests, Changes, previews, the Desktop and Agents views, Plan, citations and attachments — is listed in a compact rail to the right of the chat; hover to see the labels, click a row to open it. The workspace pane remembers per session whether it was open, and a session starts with it closed. Tabs that are not artifacts (Findings, Inbox, Todo…) stay in the add-tab menu, and `?tab=` links still open the tab they name.

**Agent / Ask Moves Into the Composer**

The Agent / Ask switch moves from the header into a dropdown inside the composer. The same dropdown holds the modes for each side — Agent modes (Code, Data) or Ask modes (Auto, Q\&A, Plan) — and switching Agent/Ask flips the composer immediately with that side's default mode selected.

**Review Analytics**

Analytics > Review now shows what became of Review's findings (fixed, rejected, ignored) for the built-in review and for each custom reviewer, and how each version of a custom reviewer's instructions performed.

**GitLab Merge Trains**

Devin Review can now add GitLab merge requests to their project's merge train. Editing a pending inline comment on a GitLab merge request keeps it at its original location.

**Find Skips Collapsed Files**

Find in Devin Review now skips collapsed files by default. Turn off "Skip collapsed files" in the find filter menu to search them; the choice is remembered.

**Chapter Guide File Cards**

Review's chapter guide lists changed files in chapter order with clearer filenames and directory paths; mark individual files or entire chapters as viewed without leaving the guide. Selecting "View as sections" restores the guide's chapters even if you previously saved File tree view.

**Keyboard: Auto-merge Shortcut and Shortcuts Dialog**

Pressing `m` in standalone Devin Review now enables auto-merge when the button offers it, and the Review keyboard shortcuts dialog no longer repeats identical key combinations.

**Clearer Status When a PR Updates or a Code Host Is Slow**

Devin Review distinguishes a newly pushed commit from an existing commit that is ready to view and from analysis updates that leave the code unchanged. When GitHub will not accept a Review comment because the file or line is no longer in the diff, Review says so instead of a generic error. When a code host is slow or not answering, Review and the session's pull request tab say the code host did not respond and keep retrying (after one attempt, not three) instead of saying you have no access to the repository.

**Unlink Devin from a Finding**

You can unlink Devin from a security finding from the findings table or the finding's details, so it can be fixed again.

**Copy as Markdown Includes Validation and Review Reasons**

Copy as Markdown on a finding now includes the sandbox validation result and evidence, and the reason the finding was reviewed or dismissed. A board-backed sealed finding can be edited through the content tool, with the changes shown in Activity.

**Security Sidebar**

Fix sessions are listed in their own Sessions section below Scans instead of nested under each scan or connection, with Scans showing 5 rows at a time; the empty Sessions list matches the main sidebar's wording; and the "Introducing Devin Security" dialog no longer appears over a session page.

**Turn Off Automatic CI Follow-up for your Organization**

Org admins can turn off Devin's automatic CI follow-up under Settings > Customization > Pull requests, and reach the switch from the CI checks tile on Cost Breakdown. It stays on by default, and asking Devin directly still works.

**Session Details in PR Descriptions Can Be Turned Off**

Admins can turn off the automatic session links and requester details in Devin-generated PR descriptions from Devin Sessions settings. The setting is on by default and takes effect when sessions start or resume.

**Organization Picture for Every Organization**

Admins of non-enterprise organizations can now upload or remove an organization picture in Settings > General.

**Plugin MCP Server URLs: Region Choices and Readable Settings**

A plugin can now offer a choice of regions for its MCP server (Datadog uses this for its sites), and that choice is shown before the first sign-in instead of defaulting to one region. The Server URL field shows the part you type as its own input and lists long query parameters one per row. When a plugin moves its server to a new URL, existing installations connect at the new URL without reconnecting.

**Enterprise MCP Editor Asks for a Required OAuth Client**

When adding an MCP server from the catalog that needs your own OAuth client (such as Google Calendar) for the whole enterprise, the form opens the OAuth credentials section, shows the setup steps and asks for the client ID before the server can be created, instead of failing silently.

**November 12, 2026**

### Sessions & Workspace

**Same-kind requests merge into one card**

When Devin asks for several things of the same kind at once (credentials, approvals, network access), they appear together in one compact card instead of a stack of cards.

**"Reminder set" row**

When Devin sets itself a reminder, the session shows a "Reminder set" row with the time or schedule and a link to the reminder.

**Repo file links show as pills**

Bare links to a file on github.com or gitlab.com appear in chat as a short pill naming the file, lines and commit instead of the full URL.

**Drag an open session by its header**

Drag an open session by its pane header onto a sidebar folder, Recent or another session, with the same result as dragging its sidebar row.

**Clearer upload and folder-attach errors**

Attaching a folder no longer fails when one file cannot be read (the rest is attached and you are told what was left out), and uploads blocked by your network's security policy say so with the reason.

### Devin Review

**Redesigned Devin Review page**

The redesigned Devin Review page is now available to all organizations: merge controls, the actions menu and the diff-size pill live in the top bar, the sidebar collapses out of the way, and findings are presented in the redesigned cards and panels.

**"Automatically fix Devin Review findings" setting**

Whether Devin fixes Devin Review findings on pull requests from its sessions is now its own setting, separate from Responding to bots. Each organization's default is in Settings > Devin, under Pull requests, and each person can change it for their own sessions in Settings > Preferences, under Devin sessions.

### Security

**Scan syncs with several connections**

When starting a Security scan you can pick several connections so its findings sync to more than one external destination.

**Source filter lists each connection**

The Source filter on the Findings page lists each connection separately, so findings can be filtered to a single scanner connection.

**Named Custom connections**

A Custom security connection now asks for a connection name (for example "Semgrep"), which is the name it is shown under.

**Delete a finding tag org-wide**

Hover a tag in the Findings filter and click the X to delete it from every finding at once.

**Each finding has its own chat**

The chat button on a finding opens that finding's own chat; the Findings page launcher keeps its general chat.

**Finding status changes can be undone**

Dismissing a finding or marking it reviewed shows exactly what changed, with an Undo button (or Cmd/Ctrl+Z).

**Veracode and Black Duck findings sources (closed beta)**

Security connections can import findings from Veracode (Static, Dynamic, Manual and SCA findings) and Black Duck (vulnerable components of a project version). Dismissing or reopening a finding writes back as a Veracode mitigation or Black Duck remediation status. Available as a closed beta.

### Enterprise & Settings

**Seven more optional GitHub permissions**

Enterprise admins can stop Devin from using the GitHub code quality, deployments, pages, discussions, repository projects, repository hooks and packages permissions under Optional GitHub permissions.

**Approve personal secrets shared with service users**

Anyone who can write to a session can approve a request to use a personal secret they shared with a service user.

**Enterprise-disabled agent modes are shown**

Organization settings show agent modes disabled by your enterprise and explain who can enable them.

**Login page explains IP allowlist denials**

Users signing in from outside their organization's IP allowlist see why on the login page, including their current IP, instead of a blank login page.

**Multiple installations per MCP in Customize**

MCPs signed in with several accounts list each installation separately with its own settings; add another installation from the marketplace card; every installation offers Disconnect and Uninstall with a short explanation. Supabase can switch between read-only and full access from its settings.

**Pylon EU region**

Admins can connect a Pylon workspace hosted in Pylon's EU region, and Pylon issue links open the EU app for those workspaces.

**Bitbucket Data Center clone fixes**

Clones through Devin's git proxy work with Bitbucket Data Center `/scm/` clone URLs and on instances with Basic authentication disabled (the default in version 10).

**MCP tool permissions**

Set each MCP tool to Allow, Needs approval or Block from Customize. Enterprise admins can also limit individual tools to specific organizations.

### Integrations

**Mention-only Slack thread mode**

New Slack thread mode "Reply in the same thread, only when mentioned": Devin stays in the thread but only responds to messages that tag it. Available as the org default and as a personal override.

**Archiving a session archives its Slack code channel**

Archiving a Devin session also archives its dedicated Slack code channel.

**Teams: Devin edits messages in place**

In Microsoft Teams, when Devin edits a message it is updated in place, and a replaced message collapses behind "Show earlier".

**Slack working status for @mentions**

In Slack threads with several people, Devin shows its working status right away when you @mention it, and after it starts acting on an untagged reply.

### Automations & Oncall

**Readable schedules on automation cards**

Automation cards show a readable schedule ("Weekly on Thursday at 6:00 PM...") for schedules that previously showed raw RRULE text.

**Oncall report notifications and PR panel**

Oncall report notifications in Slack open with the report period and list action items as bullets; the report's pull requests panel shows each PR's state, repository and date (GitLab orgs see "Merge requests").

