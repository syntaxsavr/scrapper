#!/bin/bash
python3 -m venv venv
source venv/bin/activate

# packages
pip install django requests beautifulsoup4

# project
django-admin startproject scrapper_project .

# app - USE DIFFERENT NAME (not scrapper)
python manage.py startapp webscraper