// Responsible for every call to the Saathi API.
// Each method sends one request with the login token and returns the reply.
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;

namespace Saathi.Web.Services;

// An error reported by the API (or a network problem), with a message that is safe to show to the user.
public class ApiException(string message) : Exception(message);

// Talks to the Saathi API on behalf of the logged-in user.
public class ApiClient(HttpClient http, AuthState auth)
{
    // The API names fields like customer_id; this maps them to C# names like CustomerId.
    private static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    // Logs in and returns the token, name and role.
    public Task<LoginResponse> Login(string agentId, string passcode) =>
        Send<LoginResponse>(HttpMethod.Post, "/auth/login", new { agent_id = agentId, passcode });

    // Lists the customers the logged-in agent may see.
    public Task<List<CustomerListItem>> GetCustomers() =>
        Send<List<CustomerListItem>>(HttpMethod.Get, "/customers", null);

    // Asks a question about a customer. Leave sessionId null to start a new session.
    public Task<ChatResponse> Chat(string customerId, string? sessionId, string question) =>
        Send<ChatResponse>(
            HttpMethod.Post, "/chat", new { customer_id = customerId, session_id = sessionId, question });

    // Creates a pending renewal draft for a customer.
    public Task<Draft> CreateDraft(string customerId) =>
        Send<Draft>(HttpMethod.Post, "/drafts", new { customer_id = customerId });

    // Approves a pending draft.
    public Task<ApproveResult> ApproveDraft(string draftId) =>
        Send<ApproveResult>(HttpMethod.Post, $"/drafts/{draftId}/approve", null);

    // Sends an approved draft (simulated).
    public Task<SendResult> SendDraft(string draftId) =>
        Send<SendResult>(HttpMethod.Post, $"/drafts/{draftId}/send", null);

    // Returns the Renewal Radar worklist.
    public Task<List<RadarRow>> GetRadar() =>
        Send<List<RadarRow>>(HttpMethod.Get, "/radar/worklist", null);

    // Lists the drafts with one status (PENDING, APPROVED or SENT). Supervisors only.
    public Task<List<Draft>> ListDrafts(string status) =>
        Send<List<Draft>>(HttpMethod.Get, $"/drafts?status={status}", null);

    // Returns the newest audit events. Supervisors only.
    public Task<List<AuditEvent>> GetAudit() =>
        Send<List<AuditEvent>>(HttpMethod.Get, "/audit", null);

    // Asks the API to check the whole audit chain. Supervisors only.
    public Task<VerifyResult> VerifyAudit() =>
        Send<VerifyResult>(HttpMethod.Get, "/audit/verify", null);

    // Returns the usage counts. Supervisors only.
    public Task<Usage> GetUsage() =>
        Send<Usage>(HttpMethod.Get, "/usage", null);

    // Sends one request with the login token. A failed call throws an ApiException with the API's own message.
    private async Task<T> Send<T>(HttpMethod method, string path, object? body)
    {
        using var request = new HttpRequestMessage(method, path);
        if (auth.Token is not null)
        {
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", auth.Token);
        }
        if (body is not null)
        {
            request.Content = JsonContent.Create(body, body.GetType(), options: Json);
        }

        HttpResponseMessage response;
        try
        {
            response = await http.SendAsync(request);
        }
        catch (HttpRequestException)
        {
            throw new ApiException("Cannot reach the API");
        }

        using (response)
        {
            if (!response.IsSuccessStatusCode)
            {
                throw new ApiException(await ReadError(response));
            }
            return (await response.Content.ReadFromJsonAsync<T>(Json))!;
        }
    }

    // Reads the message from the API's error body, or describes the status code when there is no body.
    private static async Task<string> ReadError(HttpResponseMessage response)
    {
        if (response.Content.Headers.ContentType?.MediaType == "application/json")
        {
            var error = await response.Content.ReadFromJsonAsync<ErrorBody>(Json);
            return error!.Error.Message;
        }
        return $"Request failed with status {(int)response.StatusCode}";
    }
}
