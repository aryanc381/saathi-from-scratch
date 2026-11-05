// Responsible for starting the Saathi web app: it reads API_URL and registers the API client and the login state.
using Saathi.Web;
using Saathi.Web.Services;

var builder = WebApplication.CreateBuilder(args);

var apiUrl = builder.Configuration["API_URL"];
if (apiUrl is null)
{
    throw new InvalidOperationException("API_URL is not set");
}

builder.Services.AddRazorComponents().AddInteractiveServerComponents();

// Each browser session (a Blazor circuit) gets its own HttpClient, login state and API client.
builder.Services.AddScoped(_ => new HttpClient { BaseAddress = new Uri(apiUrl) });
builder.Services.AddScoped<AuthState>();
builder.Services.AddScoped<ApiClient>();

var app = builder.Build();

app.UseStaticFiles();
app.UseAntiforgery();
app.MapRazorComponents<App>().AddInteractiveServerRenderMode();

app.Run();
