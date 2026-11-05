// Responsible for remembering who is logged in during one browser session.
namespace Saathi.Web.Services;

// Holds the login of one browser session.
public class AuthState
{
    public string? Token { get; private set; }
    public string? Name { get; private set; }
    public string? Role { get; private set; }

    public bool IsLoggedIn => Token is not null;
    public bool IsSupervisor => Role == "supervisor";

    // Stores the result of a successful login.
    public void SignIn(string token, string name, string role)
    {
        Token = token;
        Name = name;
        Role = role;
    }

    // Forgets the login.
    public void SignOut()
    {
        Token = null;
        Name = null;
        Role = null;
    }
}
