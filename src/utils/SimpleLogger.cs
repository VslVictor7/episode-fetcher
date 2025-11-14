using System;

namespace AnimeMonitor;

public sealed class SimpleLogger
{
    private readonly string _name;

    public SimpleLogger(string name)
    {
        _name = name;
    }

    private void Write(string level, string message)
    {
        var ts = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
        Console.WriteLine($"{ts} [{level}] {_name}: {message}");
    }

    // --- LOG METHODS ---

    public void Debug(string msg)
        => Write("DEBUG", msg);

    public void Info(string msg)
        => Write("INFO", msg);

    public void Warn(string msg)
        => Write("WARN", msg);

    public void Error(string msg)
        => Write("ERROR", msg);

    // --- OVERLOADS COM EXCEÇÃO (compatibilidade) ---

    public void Warn(Exception ex, string msg)
        => Write("WARN", $"{msg} | Exception: {ex}");

    public void Error(Exception ex, string msg)
        => Write("ERROR", $"{msg} | Exception: {ex}");
}
