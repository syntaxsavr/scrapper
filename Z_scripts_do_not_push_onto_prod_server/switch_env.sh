#!/bin/bash
ENV=$1
if [[ "$ENV" == "production" || "$ENV" == "testing" || "$ENV" == "development" ]]; then
    export ENVIRONMENT=$ENV
    echo "Switched to $ENV environment"
else
    echo "Usage: ./switch_env.sh [development|testing|production]"
fi
#aaaaaaaaarghhhhhhhhhhhhhh