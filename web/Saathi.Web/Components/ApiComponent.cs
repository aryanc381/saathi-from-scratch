// Responsible for what every component that calls the API shares: running a call and keeping its error message.
using Microsoft.AspNetCore.Components;
using Saathi.Web.Services;

namespace Saathi.Web.Components;

// The base class of every component that calls the API.
public abstract class ApiComponent : ComponentBase
{
    [Inject]
    protected ApiClient Api { get; set; } = default!;

    // The message of the last failed call, shown on the page. Null when the last call worked.
    protected string? Error { get; private set; }

    // Runs one API call. An error from the API is kept in Error instead of crashing the page.
    protected async Task Run(Func<Task> call)
    {
        Error = null;
        try
        {
            await call();
        }
        catch (ApiException e)
        {
            Error = e.Message;
        }
    }
}
