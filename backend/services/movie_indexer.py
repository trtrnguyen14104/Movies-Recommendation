from services.chromadb_service import get_movies_collection
from services.embedding_service import embed_text
from tmdb_service import get_popular_movies

async def index_movies():
    collection = get_movies_collection()

    movies = await get_popular_movies(page=1)

    ids = []
    docs = []
    embeddings = []
    metadatas = []

    for movie in movies["results"]:

        text = f"""
        Title: {movie['title']}

        Overview:
        {movie.get('overview', '')}

        Genres:
        {movie.get('genre_ids', [])}
        """

        embedding = embed_text(text)

        if embedding:
            ids.append(str(movie["id"]))
            docs.append(text)
            embeddings.append(embedding)

            metadatas.append({
                "title": movie["title"]
            })

    collection.upsert(
        ids=ids,
        documents=docs,
        embeddings=embeddings,
        metadatas=metadatas
    )