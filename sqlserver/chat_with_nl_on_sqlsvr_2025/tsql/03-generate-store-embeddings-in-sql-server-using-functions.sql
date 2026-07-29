USE TestDB
GO

-- Inspect existing vectors (quick sanity check)
SELECT TOP (5) * FROM products_vector;
GO


-- Testing the embeddings workflow
SELECT TOP (1)
    P.productid,
    AI_GENERATE_EMBEDDINGS(P.name USE MODEL MyAzureOpenAIModel) AS embedding
FROM products AS P;
GO


/* Generate and store embeddings in SQL Server
-- Insert embeddings for product names (ranker model)
-- Note: No chunking is applied here. This uses single-shot embedding, 
         but we could rely on AI_GENERATE_CHUNKS for chunking.
*/
INSERT INTO products_vector ([productid], [embedding_ranker])
SELECT
    P.productid,
    AI_GENERATE_EMBEDDINGS(P.name USE MODEL MyAzureOpenAIModel) AS embedding
FROM products AS P;


-- Verify inserts
SELECT TOP (5) * FROM products_vector;
GO



-- Demo: Chunk product descriptions
-- NOTE: CHUNK_SIZE = 9 and OVERLAP = 7 is intentionally bad:
--       - too small → over‑chunking → noisy embeddings
--       - too much overlap → redundant chunks → higher cost
SELECT TOP (5) *
FROM products AS P
CROSS APPLY
    AI_GENERATE_CHUNKS (
        SOURCE = P.description,
        CHUNK_TYPE = FIXED,
        CHUNK_SIZE = 9,   -- ⚠ too small → loses meaning
        OVERLAP = 7       -- ⚠ too high → duplicates content
    ) AS c;


/* For testing purposes only
-- Demo: Chunk + embed in one query
-- Same chunking warnings apply here
*/
SELECT TOP (5)
    P.productid,
    AI_GENERATE_EMBEDDINGS(P.name USE MODEL MyAzureOpenAIModel) AS embedding,
    *
FROM products AS P
CROSS APPLY
    AI_GENERATE_CHUNKS (
        SOURCE = P.description,
        CHUNK_TYPE = FIXED,
        CHUNK_SIZE = 9,   -- ⚠ avoid tiny chunks
        OVERLAP = 7       -- ⚠ avoid excessive overlap
    ) AS c;

-- more about chunking testing examples
-- For more information on chunking and its impact on embedding quality, refer to the official documentation.

-- Table variable for manual chunking tests
DECLARE @textchunk TABLE
(
    text_id INT IDENTITY(1,1) PRIMARY KEY,
    text_to_chunk NVARCHAR(MAX)
);


-- Insert sample long texts
-- (Good for testing chunk size behavior)
INSERT INTO @textchunk (text_to_chunk)
VALUES
('All day long we seemed to dawdle through a country which was full of beauty of every kind. Sometimes we saw little towns or castles on the top of steep hills such as we see in old missals; sometimes we ran by rivers and streams which seemed from the wide stony margin on each side of them to be subject to great floods.'),
('My Friend, Welcome to the Carpathians. I am anxiously expecting you. Sleep well to-night. At three to-morrow the diligence will start for Bukovina; a place on it is kept for you. At the Borgo Pass my carriage will await you and will bring you to me. I trust that your journey from London has been a happy one, and that you will enjoy your stay in my beautiful land. Your friend, DRACULA');


-- Chunk the sample text
-- CHUNK_SIZE = 50 is reasonable for narrative text
-- ENABLE_CHUNK_SET_ID groups chunks from the same input
SELECT c.*
FROM @textchunk t
CROSS APPLY
   AI_GENERATE_CHUNKS(
       SOURCE = text_to_chunk,
       CHUNK_TYPE = FIXED,
       CHUNK_SIZE = 50,          -- ✔ balanced chunk size
       ENABLE_CHUNK_SET_ID = 1   -- groups chunks by source text
   ) AS c;
