# Case

**Various case/incident related commands**

## Clone
It may be useful to clone a case from the production environment to the dev environment. This will of course require a configuration file
with API keys for both environments. The syntax is `xsoar-cli case clone --dest TEXT --source TEXT CASENUMBER` where default environments for `dest` and `source` are "dev" and "prod", respectively.

#### Example invocation
```
xsoar-cli case clone --dest prod --source dev 312412  # explicitly using the default options
xsoar-cli case clone 312412                           # shorthand for the same invocation as above
```


## Create
It may be useful to create a case in the dev environment. The syntax is `xsoar-cli case create [OPTIONS] [NAME] [DETAILS]` where NAME and
DETAILS are optional. If NAME and DETAILS are not filled in, then default values are used.
#### Example invocation
```
xsoar-cli case create 312412
xsoar-cli case create 312412 "This is the name/title of the case" "This is some descriptive text on what the case is about."
```


## Get
It may be useful to quickly fetch some case data. The syntax is `xsoar-cli case clone [OPTIONS] CASENUMBER` and the command outputs raw JSON indented with 4 whitespaces to make the resulting output at least somewhat readable.
#### Example invocation
```
xsoar-cli case get 312412
```
