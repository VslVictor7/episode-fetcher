using System.Text.Json.Serialization;
using AnimeMonitor;

[JsonSerializable(typeof(EpisodeState))]
public partial class AnimeMonitorJsonContext : JsonSerializerContext { }