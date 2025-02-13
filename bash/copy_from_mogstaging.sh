#!/bin/bash
open smb://mog-staging.pluralpp.plr/d$
rsync -ruv "/Volumes/d$/LTC_PROJECT/*" "/Users/rui/LTC_PROJECT/."