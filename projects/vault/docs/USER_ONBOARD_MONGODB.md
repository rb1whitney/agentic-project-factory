# Onboard Mongo Database for Dynamic Credentials and Usage

This document outlines the procedures for Clover engineers to onboard MongoDB databases with the ultimate goal of obtaining dynamic/short-lived credentials for use with mongosh or other database tools.

## Copy Existing Database Configuration File

Once your database has been created in the proper [place](https://github.corp.clover.com/clover/clover-dev-atlas/wiki/MongoDB-Atlas-Administration-Guide-for-Infrastructure-Admins#howto-create-a-new-database), you should copy an existing configuration and change the names to match your database.

A good example to start with is the loyalty-dev database configuration [here](https://github.corp.clover.com/clover/vault/blob/a4ea80044e9d978c71512c17287894bf7d479768/config/json_workspaces/nonprod/namespaces/atlas/database-loyalty-dev.json).  If you have a new database called **foo-dev** simply copy the file to database-foo-dev.json and find/replace everything that says `loyalty-dev` with `foo-dev`
