# ===============================
#   STAGE 1 — BUILD
# ===============================
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build

WORKDIR /src

COPY AnimeMonitor.csproj ./
RUN dotnet restore

COPY . ./

RUN dotnet publish -c Release \
    -o /app/publish \
    --self-contained true \
    -r linux-x64 \
    /p:PublishSingleFile=true \
    /p:PublishTrimmed=true \
    /p:StripSymbols=true \
    /p:IncludeNativeLibrariesForSelfExtract=true

    
# ===============================
#   STAGE 2 — RUNTIME (CHISELED)
# ===============================
FROM mcr.microsoft.com/dotnet/runtime-deps:10.0-noble-chiseled AS final

WORKDIR /app

COPY --from=build /app/publish .

ENTRYPOINT ["./AnimeMonitor"]