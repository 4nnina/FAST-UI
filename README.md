# FAST-UI: Fair Assignment System for Sequential Tasks

Fairness is a complex, context-dependent concept that varies across cultures and stakeholder perspectives. Despite its ambiguity, it plays a critical role in real-world scenarios where competing interests, resources, and time-based constraints must be balanced.
In this demo, we present FAST, a framework designed to determine fair sequential task assignments among multiple stakeholders. FAST takes as input constraints and preferences of different stakeholders over time and produces *local* and *global* solutions, namely fair solutions considering only one stakeholder or all the stakeholders simultaneously.

### Running the Web App

Firstly, follow the instructions in 📁`src` and 📁`dataset` folders.

The database is already populated with the real preferences of professors at the University of Verona. 

```cmd
cd web_ui
python app.py
```

###### Existing users

For testing purposes, you can use the following credentials to log in:

| Username | Password |
| -------- | -------- |
| admin    | admin    |
| prof1    | prof1    |
| prof4    | prof4    |
| ...      | ...      |
| prof112  | prof112  |
