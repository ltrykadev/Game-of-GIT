"""Game of GIT entry point: launch the web UI."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "gameofgit.web.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
