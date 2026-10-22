# Skating song webiste

## Basic Functionality:

### Main Interaction

There are 2 main search options:
- Music artist, song, genre, theme (e.g. pirate of the caribbean, classical, pop) search --> Gets a list of all the song that have a least one skating program attached to. When you pick a song, you get a list of all the skaters that have at least one performance on this song. When you pick a skater, you get all the known performance he has with this song.
- Skater name --> All the seaons he has been part of. When you pick a season, you get all the competitions he has been part of. And for each competitions, you get a video of the performance (if there is one).

### Identified needed components

#### Data source

There needs to be a source of data for the music and the skaters + programs.

For the music part, we only need to list the songs that have been used in skating program but should avoid duplicates, that might be harder than it seems.

For the skaters, we need as many as possible going from today's skaters to as far back as we can. We don't know yet what the best source of data for this is.

We expect data that provides the program as well and ideally the video of the performance.

To make it all easier, we only need the ISU related competitions.

Many recent performance are clearly linked to an official ISU video. But most older performance are not.
We need a mechanism to take video link submissions (youtube only) for the remaining video and we should be able to automatically extract the skater, program and song and match it to an existing item or create a new one if there is none (we really need to avoid duplicates).

#### Adressing possible fails

There should be a clean admin panel to fix performance that got wrongly assigned.
There should be a flag for users to signal a performance that got wrongly assigned for the admin to review.

## Styling

For now it should remain simple and elegant. 

## Tech stack

The repo needs to be easily maintanable, use provably good tools and librairies.

Using react could be nice because it has plenty of documentation but it seems quite bloated. Be the judge, what is the best stack for our project. For that, act as a system engineer to determine the best frontend and backend for this project. The backend might use multiple language. For instance python might be easier to read and maintains when it comes to scraping.

I have access to a homeserver, cloudflare tunnels,... But we need to evaluate the best way to host my project (I am ready to pay a little if needed)


## AI harness stack

You should ask me for what tools you need installed before starting the implementation.
For instance: Postgresql MCP, Playwright MCP,..., any cli, mcp, plugin,...
Even skills to build the UI or the deployment.
Don't bloat the context, tools need to be justified.


