---
sidebar_position: 3
title: Linear
---

# Linear

Linear is a tracker-only integration - Maestro syncs issues from Linear and updates their status as tasks move through the pipeline.

You still need a separate **GitHub** or **GitLab** connection as the codebase.

## API key

Create an API key from [Linear Settings > API](https://linear.app/settings/api).

## Add the connection

1. Go to **Settings > Connections**
2. Click **Add Connection** and select **Linear**
3. Paste your API key
4. Select the **Project** to sync issues from

## What happens

- Issues from the selected project sync to the Maestro **Tasks** page
- Task status updates in Maestro are reflected back in Linear
