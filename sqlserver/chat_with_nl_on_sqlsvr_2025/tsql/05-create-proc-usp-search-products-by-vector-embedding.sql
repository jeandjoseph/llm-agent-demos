---TESTING ONLY
/* Declare a VECTOR variable to hold the query embedding */
DECLARE @query VECTOR(1536);

/* Generate the embedding for the natural‑language search query */
SET @query = AI_GENERATE_EMBEDDINGS(
    N'I’m looking for a lightweight laptop with long battery life.'
    USE MODEL MyAzureOpenAIModel
);



/* 
Return the 10 most similar products based on cosine distance.
- VECTOR_DISTANCE('cosine', product_vector, @query) computes similarity.
- 1 - distance converts it into a similarity score (higher = more similar).
- Results are ordered from most relevant to least.
*/
SELECT TOP 100
    P.productid,
    P.name,
    P.category,
    PRS.abstractive_summary,
    ROUND(1 - VECTOR_DISTANCE('cosine', PV.embedding_ranker, @query), 4) AS similarity
FROM dbo.products AS P
INNER JOIN dbo.products_vector AS PV
    ON P.productid = PV.productid
INNER JOIN dbo.product_review_summary AS PRS
    ON P.productid=PRS.productid
ORDER BY VECTOR_DISTANCE('cosine', PV.embedding_ranker, @query);
GO

/*************************************************************************************
        CREATE PROCEDURE FOR VECTOR-BASED PRODUCTS SEARCH 
**************************************************************************************/
--CREATE PROC
CREATE OR ALTER PROCEDURE usp_find_similar_products_by_embedding
(
    @query_text NVARCHAR(MAX),
    @top_n INT = 10,
    @model_name SYSNAME = 'MyAzureOpenAIModel'
)
AS
BEGIN
    SET NOCOUNT ON;

    /* Declare the output vector */
    DECLARE @query VECTOR(1536);

    /* Build dynamic SQL for AI_GENERATE_EMBEDDINGS */
    DECLARE @sql NVARCHAR(MAX) = N'
        SET @out_query = AI_GENERATE_EMBEDDINGS(
            @in_text
            USE MODEL ' + QUOTENAME(@model_name) + N'
        );
    ';

    /* Execute dynamic SQL and capture the embedding */
    EXEC sp_executesql
        @sql,
        N'@in_text NVARCHAR(MAX), @out_query VECTOR(1536) OUTPUT',
        @in_text = @query_text,
        @out_query = @query OUTPUT;

    /* Vector similarity search with dynamic recommendation */
    SELECT TOP (@top_n)
        P.name,
        P.category,
        PRS.abstractive_summary,
        PRS.positive_score,
        PRS.neutral_score,
        PRS.negative_score,
        CONCAT(
            ROUND(S.sim * 100, 1), '% — ',
            CASE 
                WHEN S.sim >= M.max_sim * 0.90 THEN 'Highly recommended for your request'
                WHEN S.sim >= M.max_sim * 0.70 THEN 'Recommended for your request'
                ELSE 'Low relevance for your request'
            END
        ) AS similarity_readable
    FROM dbo.products AS P
    INNER JOIN dbo.products_vector AS PV
        ON P.productid = PV.productid
    INNER JOIN dbo.product_review_summary AS PRS
        ON P.productid=PRS.productid

    /* Compute similarity once */
    CROSS APPLY (
        SELECT (1 - VECTOR_DISTANCE('cosine', PV.embedding_ranker, @query)) AS sim
    ) AS S

    /* Compute max similarity dynamically */
    CROSS JOIN (
        SELECT MAX(1 - VECTOR_DISTANCE('cosine', embedding_ranker, @query)) AS max_sim
        FROM products_vector
    ) AS M

    ORDER BY S.sim DESC;
END;
GO


--How to call it
-- Custom search text
/*
Show me products that offer premium sound quality.
Find wireless earbuds with noise cancellation.
I’m looking for a lightweight laptop with long battery life.
Show me a fitness smartwatch with heart rate monitor.
Find a smart home device with voice control.
Show me options for smart home automation.
Do you have a gaming controller with haptics?
Show me a portable sound system for travel.
Find an eco-friendly home appliance.
*/
EXEC usp_find_similar_products_by_embedding
    @query_text = N'Find an eco-friendly home appliance.',
    @top_n = 5,
    @model_name = 'MyAzureOpenAIModel';
