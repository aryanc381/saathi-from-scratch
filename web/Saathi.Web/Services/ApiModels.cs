// Responsible for the C# shapes that match the JSON the Saathi API sends back.
// Names map from snake_case, for example customer_id becomes CustomerId.
namespace Saathi.Web.Services;

// The reply to a login: the token, the user's name and their role.
public record LoginResponse(string Token, string Name, string Role);

// Where a statement came from: the PDF, the clause in it and its version.
public record Citation(string SourceId, string ClauseId, string Version);

// What the agent is asking about, and how sure the model is.
public record IntentResult(string Label, double Confidence);

// The reply to a chat question. When Blocked is true, Reason says why.
public record ChatResponse(
    string? SessionId, string Answer, List<Citation> Citations, IntentResult? Intent, bool Blocked, string? Reason);

// One row of the customer list.
public record CustomerListItem(string CustomerId, string Name, string Language, bool Consent, string RenewalStatus);

// A renewal message draft.
public record Draft(
    string DraftId, string CustomerId, string AgentId, string Text, List<Citation> Citations, string Status,
    string? ApprovedBy);

// The reply to approving a draft.
public record ApproveResult(string DraftId, string Status, string ApprovedBy);

// The reply to sending a draft. Nothing is really sent.
public record SendResult(string DraftId, string Status);

// One customer on the Renewal Radar worklist.
public record RadarRow(
    string CustomerId, string Name, int DaysToRenewal, double Score, List<string> TopFactors, string Status);

// One row of the audit log.
public record AuditEvent(int Id, string Ts, string Actor, string Type, string Payload, string Hash);

// The result of checking the audit chain. BrokenAt is the first bad event.
public record VerifyResult(bool Valid, int? BrokenAt, int Count);

// The counts shown on the supervisor screen.
public record Usage(int Chats, int Blocked, Dictionary<string, int> DraftsByStatus);

// The code and message inside an API error.
public record ErrorDetail(string Code, string Message);

// The body the API sends when a request fails.
public record ErrorBody(ErrorDetail Error);
