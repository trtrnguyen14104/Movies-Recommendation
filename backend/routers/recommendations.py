"""
Router goi y phim voi he thong Genre Weighting.
Thuat toan: Content-Based Filtering co trong so hanh dong.

He thong diem:
    - Bam THICH mot phim     : +3 diem cho moi genre cua phim do
    - Xem TRAILER mot phim   : +2 diem cho moi genre cua phim do
    - Bam vao DETAIL mot phim: +1 diem cho moi genre cua phim do

Vi du thuc te:
    User thich Batman   (Action=28, Adventure=12) → Action+3, Adventure+3
    User xem trailer    Avengers (Action=28, Sci-Fi=878) → Action+2, Sci-Fi+2
    User bam vao detail Thor (Action=28, Fantasy=14) → Action+1, Fantasy+1

    Tong diem genre:
        Action    (28) = 3 + 2 + 1 = 6 diem  ← quan trong nhat
        Adventure (12) = 3              = 3 diem
        Sci-Fi   (878) = 2              = 2 diem
        Fantasy   (14) = 1              = 1 diem

    → He thong se goi y phim Action la chu yeu
"""

from fastapi import APIRouter, Query
from services import tmdb_service
from services.tmdb_service import image_url

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/goi-y")
async def recommend_by_genres(
    genre_scores: str = Query(
        ...,
        description=(
            "Diem tung genre, dinh dang 'genre_id:diem' cach nhau bang dau phay. "
            "Vi du: '28:6,12:3,878:2,14:1' "
            "(Action 6 diem, Adventure 3 diem, Sci-Fi 2 diem, Fantasy 1 diem)"
        )
    ),
    exclude_ids: str = Query(
        "",
        description="Cac movie_id can bo qua (phim da tuong tac roi). Vi du: '272,1726,76338'"
    ),
    limit: int = Query(
        12,
        ge=1,
        le=20,
        description="So luong phim muon lay ve, mac dinh 12"
    ),
):
    """
    API goi y phim dua tren diem genre co trong so.
    Frontend tinh diem roi gui len, backend dung diem do de chon genre va tim phim.

    Vi du goi API:
        GET /recommendations/goi-y
            ?genre_scores=28:6,12:3,878:2
            &exclude_ids=272,1726
            &limit=12

    Vi du tra ve:
        {
            "results": [...],
            "total": 12,
            "top_genres": [
                {"genre_id": "28", "score": 6},
                {"genre_id": "12", "score": 3},
                {"genre_id": "878", "score": 2}
            ]
        }
    """

    # ----------------------------------------------------------------
    # BUOC 1: Phan tich chuoi genre_scores thanh dict {genre_id: diem}
    #
    # Input:  "28:6,12:3,878:2,14:1"
    # Output: {"28": 6, "12": 3, "878": 2, "14": 1}
    #
    # Cach hoat dong:
    #   - Tach chuoi theo dau phay → ["28:6", "12:3", "878:2", "14:1"]
    #   - Moi phan tu tach theo dau hai cham → ("28", "6")
    #   - Chuyen diem sang so nguyen → {"28": 6}
    # ----------------------------------------------------------------
    genre_weight_map = {}
    for item in genre_scores.split(","):
        item = item.strip()
        if ":" not in item:
            continue  # Bo qua neu sai dinh dang
        parts = item.split(":")
        if len(parts) != 2:
            continue
        genre_id, score_str = parts[0].strip(), parts[1].strip()
        if genre_id and score_str.lstrip("-").isdigit():
            score = int(score_str)
            if score > 0:  # Chi lay genre co diem duong (diem am la khong thich)
                genre_weight_map[genre_id] = score

    # Neu khong co genre hop le nao thi tra ve rong
    if not genre_weight_map:
        return {"results": [], "total": 0, "top_genres": []}

    # ----------------------------------------------------------------
    # BUOC 2: Sap xep genre theo diem giam dan, lay top 3
    #
    # Tai sao chi lay top 3?
    #   - Neu lay qua nhieu genre, TMDB tra ve qua it phim
    #   - Top 3 genre la nhung gi user THICH NHAT → ket qua chinh xac hon
    #
    # Input:  {"28": 6, "12": 3, "878": 2, "14": 1}
    # Output: [("28", 6), ("12", 3), ("878", 2)]  ← chi lay 3 cai dau
    # ----------------------------------------------------------------
    sorted_genres = sorted(
        genre_weight_map.items(),
        key=lambda x: -x[1]  # Sap xep giam dan theo diem
    )
    top_3 = sorted_genres[:3]
    top_genre_ids = [gid for gid, _ in top_3]

    # ----------------------------------------------------------------
    # BUOC 3: Goi TMDB lay phim theo top genre
    #
    # Ghep 3 genre_id lai thanh chuoi de truyen vao TMDB API
    # Vi du: ["28", "12", "878"] → "28,12,878"
    #
    # TMDB /discover/movie?with_genres=28,12,878
    # → tra ve phim thuoc bat ky genre nao trong 3 genre tren
    # ----------------------------------------------------------------
    with_genres_str = ",".join(top_genre_ids)
    data = await tmdb_service.get_movies_by_genre_ids(with_genres_str, page=1)
    raw_results = data.get("results", [])

    # ----------------------------------------------------------------
    # BUOC 4: Loai bo phim ma user da tuong tac roi
    #
    # Khong nen goi y lai phim ma user da thich/xem trailer/bam vao
    # exclude_ids la danh sach movie_id can loai bo
    #
    # Vi du: exclude_ids = "272,1726"
    # exclude_set = {"272", "1726"}
    # ----------------------------------------------------------------
    exclude_set = {e.strip() for e in exclude_ids.split(",") if e.strip()}

    filtered = [
        movie for movie in raw_results
        if str(movie["id"]) not in exclude_set
    ]

    # ----------------------------------------------------------------
    # BUOC 5: Tinh diem phu hop cho tung phim (Genre Match Score)
    #
    # Moi phim duoc tinh diem dua tren:
    #   - Genre cua phim do co trong top genre cua user khong?
    #   - Neu co, cong diem genre do vao diem phim
    #
    # Vi du:
    #   Phim A co genre: [28, 12]       → diem = 6 + 3 = 9
    #   Phim B co genre: [28, 878]      → diem = 6 + 2 = 8
    #   Phim C co genre: [14, 10751]    → diem = 1 + 0 = 1
    #
    # → Phim A duoc xep hang cao nhat vi khop nhieu genre quan trong
    # ----------------------------------------------------------------
    scored_movies = []
    for movie in filtered:
        movie_genre_ids = [str(gid) for gid in movie.get("genre_ids", [])]

        # Cong diem cho moi genre cua phim khop voi so thich user
        match_score = sum(
            genre_weight_map.get(gid, 0)  # Lay diem cua genre do, neu khong co thi 0
            for gid in movie_genre_ids
        )

        scored_movies.append((match_score, movie))

    # Sap xep phim theo diem khop giam dan
    # → phim khop nhieu genre quan trong nhat len dau
    scored_movies.sort(key=lambda x: -x[0])

    # ----------------------------------------------------------------
    # BUOC 6: Them URL anh va chuan bi ket qua tra ve
    #
    # TMDB chi luu ten file anh (vi du: "/abc123.jpg")
    # image_url() chuyen thanh URL day du:
    # "/abc123.jpg" → "https://image.tmdb.org/t/p/w500/abc123.jpg"
    # ----------------------------------------------------------------
    enriched = []
    for match_score, movie in scored_movies[:limit]:
        movie["poster_url"] = image_url(movie.get("poster_path"), "w500")
        movie["backdrop_url"] = image_url(movie.get("backdrop_path"), "w1280")
        movie["match_score"] = match_score  # Them diem khop de frontend hien thi neu muon
        enriched.append(movie)

    # Tra ve ket qua cuoi cung
    return {
        "results": enriched,
        "total": len(enriched),
        # Tra ve top genre de frontend hien thi "Vi ban thich Action, Adventure..."
        "top_genres": [
            {"genre_id": gid, "score": score}
            for gid, score in top_3
        ],
    }
