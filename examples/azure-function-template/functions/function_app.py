import azure.functions as func
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="test")
def test(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return func.HttpResponse(
            body=json.dumps("No problem"), headers={"Content-Type": "application/json"}
        )
    except Exception as msg:
        return func.HttpResponse("Invalid request: {0}".format(msg), status_code=400)
