<p align="center">
  <img src="public/mw-logo-only.svg" alt="Logo" height=170>
</p>

# Comms Search Tech Test

## 🎛️ Overview

Welcome to the MirrorWeb Tech Test! We'd like to see how you approach building out some new features, as well as how you work on debugging issues in existing code.

This repository contains a basic application for searching through a database of messages (not unlike MirrorWeb's Insight platform!), made up of a [Remix](https://remix.run/) frontend and a [FastAPI](https://fastapi.tiangolo.com/) API. It's in the early prototyping stages, but it has some of the core functionality in place already (e.g. authentication, basic stats dashboard, searching for messages etc). However, there are some new requirements that now need implementing...

## 🔨 Tasks

Please attempt to complete at least one of these tasks. If you want to tackle multiple then great! However, we're not expecting you to complete them all.

1. The message results list currently shows all messages - can you make this a bit more user-friendly by implementing pagination for the results list?
2. Update the selected message on the search results page to show its current status, and implement some functionality for updating the status of the currently selected message.
3. The stats dashboard when you initially log into the app can be quite slow, and can even timeout (you may have already run into these errors if you've tried running the app already). Currently if just one of the data requests to populate the dashboard times out the entire page breaks - how could you modify the way the data is loaded to ensure a single query doesn't break everything else?
4. the recent messages on the dashboard show the date they were sent, but it would be better if these were displayed in a more human readable "X minutes/hours/days ago" format - can you update the messages in this list to display the date values in this format, without resorting to any external libraries like Moment.js?

> 🚨 **Attention!** As it's still in the early stages, this app also still has some pesky bugs hanging around related to UX, accessibility, and some nasty security vulnerabilities. If you come across any of these and have an idea of how to fix them that would be great to see! If you do push any fixes (or just have some ideas on how you would fix them given more time), please document what you've done or note them down as these can be good to discuss in your interview!

## Getting started

Install:

```bash
npm install
```

Setup (you will see your login credentials logged in your console when this command finishes running):

```bash
npm run setup
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Run the API and UI together:

```bash
npm run dev
```

Navigate to `http://localhost:5173` and you should see the login page!

## Notes

- This app uses Tailwind to provide the initial styling, but you're not obligated to use this
- Please endevour to use semantic and accessible HTML markup wherever possible.
- Fixes can be made in either the Remix frontend or the FastAPI backend, bear in mind the skills you'd like to display when deciding where to make a change.

## Submitting your work

To complete the tech test you will need to clone down this GitHub repo, create a feature branch from main and do all of your work from this branch, create a single PR with all your changes back into main. When you’re ready, share your submission back with us via a private Github repository with the PR open so we can schedule it for review. We review submissions as quickly as possible. You’ll hear back from us no matter what.

Remember, we are not timing you and there is no deadline. Work at your own pace. Reach out if you're stuck or have any questions. We want you to succeed and are here to help! We won't give you much in the way of hints, but we can at least help you orient yourself about the challenge!
