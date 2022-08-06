# What To Inject



## Good Advice

Dhanji R. Prasanna wrote in a post to the google-guice Google Group:

> As a rule of thumb, Guice should generally only create:
> * what you want it to populate with other dependencies
> * what you want to be testable with mock substitutes
> * singletons
>
> If it doesn't come under one of these, you likely dont need to Guice it (example: an "Address" data model object).
