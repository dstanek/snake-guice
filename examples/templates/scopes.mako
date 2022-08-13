<html>
  <head>
    <title>Scopes Demo</title>
  </head>
  <body>
    <h1>Demo: Scoping Edition</h1>

    <h2>Sessions scoped</h2>
    <div>
        First UserProvider.get() id=${ id(user0) }
    </div>
    <div>
        Second UserProvider.get() id=${ id(user1) }
    </div>

    <h2>Request scoped</h2>
    <div>
        First RequestDataProvider.get() id=${ id(request_data0) }
    </div>
    <div>
        Second RequestDataProvider.get() id=${ id(request_data1) }
    </div>

    <h2>So, what's happening?</h2>
    <div>
        As you refresh the page a few times you will notice a few things.
        <ol>
          <li>First, the request scoped IDs will match each other. This is because
          anything that is request scoped will have the same value everytime it is
          used within the same page request.</li>
          <li>Second, the session scoped IDs will also be the same, but will persist
          between requests. Sessions are 60 seconds, so after that a new one will be
          returned.</li>
        </ol>
    </div>
  </body>
</html>