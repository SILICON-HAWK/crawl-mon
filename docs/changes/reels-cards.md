# Jobs review modes

The Jobs page now opens in a one-at-a-time Reels mode with swipe and button decisions, plus a card grid mode. Decisions are saved per profile through `/api/profile/{username}/job-actions` and can be browsed with All, Interested, and Not interested filters. Job descriptions stay collapsed until requested. Jobs without a usable URL show disabled decision controls. Runs and Profile remain on their own `/runs` and `/profile` routes.
