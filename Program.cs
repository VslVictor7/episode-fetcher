using System.Net;
using DotNetEnv;

namespace AnimeMonitor;

public class Program
{
    public static async Task Main(string[] args)
    {
        // 1) Load .env
        Env.Load();

        // 2) Simple loggers — AOT friendly, no reflection
        var mainLogger     = new SimpleLogger("Main");
        var scraperLogger  = new SimpleLogger("AnimeScraper");
        var qbLogger       = new SimpleLogger("QBittorrent");
        var trackerLogger  = new SimpleLogger("EpisodeTracker");

        try
        {
            // 3) Load config
            var config = Config.LoadFromEnv(mainLogger);

            // 4) HttpClient
            using var handler = new HttpClientHandler
            {
                CookieContainer = new CookieContainer(),
                AutomaticDecompression = DecompressionMethods.GZip 
                                       | DecompressionMethods.Deflate
            };

            using var httpClient = new HttpClient(handler)
            {
                Timeout = TimeSpan.FromSeconds(config.HttpTimeoutSeconds)
            };

            httpClient.DefaultRequestHeaders.UserAgent.ParseAdd(
                "anime-monitor/1.0 (+github.com/victorvsl7)"
            );

            // 5) Instantiate services
            var scraper = new AnimeScraper(httpClient, config, scraperLogger);
            var qbClient = new QBittorrentClient(httpClient, config, qbLogger);
            var tracker = new EpisodeTracker(config.EpisodeFile, trackerLogger);

            // 6) Load episode
            int episode = tracker.LoadNextEpisode();

            // 7) Run monitor
            await MonitorLoop(scraper, qbClient, tracker, config, mainLogger, episode);
        }
        catch (Exception ex)
        {
            mainLogger.Error("FATAL ERROR: " + ex.ToString());
        }
    }

    private static async Task MonitorLoop(
        AnimeScraper scraper,
        QBittorrentClient qbClient,
        EpisodeTracker tracker,
        Config config,
        SimpleLogger logger,
        int episode)
    {
        var cancellationToken = CancellationToken.None;

        while (true)
        {
            try
            {
                string? pageUrl = await scraper.FindEpisodePageAsync(episode, cancellationToken);

                if (pageUrl != null)
                {
                    string? magnet = await scraper.ExtractMagnetAsync(pageUrl, cancellationToken);

                    if (!string.IsNullOrWhiteSpace(magnet))
                    {
                        logger.Info($"Enviando para qBittorrent: {magnet}");

                        await qbClient.AuthenticateAsync(cancellationToken);
                        await qbClient.AddMagnetAsync(magnet, cancellationToken);

                        tracker.SaveNextEpisode(episode + 1);

                        logger.Info($"OK — Episódio {episode} concluído.");
                        break;
                    }
                    else
                    {
                        logger.Warn("Magnet não encontrado.");
                    }
                }
            }
            catch (Exception ex)
            {
                logger.Error("Erro no loop principal: " + ex.ToString());
            }

            logger.Info($"Aguardando {config.CheckIntervalSeconds / 60.0:F1} minutos...");
            await Task.Delay(TimeSpan.FromSeconds(config.CheckIntervalSeconds));
        }
    }
}