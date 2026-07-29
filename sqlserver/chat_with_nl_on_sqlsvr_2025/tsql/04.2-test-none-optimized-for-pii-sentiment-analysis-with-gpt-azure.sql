/*
Notice: because the system prompt was not optimized for the sentiment analysis task,
any pii info has been removed from the reviews in the database for this demo. 
*/
-- Variables reused for each product
DECLARE @productid INT;
DECLARE @text NVARCHAR(MAX);
DECLARE @body NVARCHAR(MAX);
DECLARE @response NVARCHAR(MAX);
DECLARE @content NVARCHAR(MAX);
DECLARE @json NVARCHAR(MAX);

-- Table to store results
DECLARE @sentiment TABLE (
    productid INT,
    feedback NVARCHAR(MAX),
    sentiment_label NVARCHAR(20),
    positive_score FLOAT,
    neutral_score FLOAT,
    negative_score FLOAT
);

-- Cursor over aggregated reviews
DECLARE review_cursor CURSOR FOR
    SELECT 
        p.productid,
        STRING_AGG(r.review_text, ' ') AS combined_reviews
    FROM products AS p
    INNER JOIN product_reviews AS r ON p.productid = r.productid
    WHERE p.productid in(1,2,18)
    GROUP BY p.productid;

OPEN review_cursor;
FETCH NEXT FROM review_cursor INTO @productid, @text;

WHILE @@FETCH_STATUS = 0
BEGIN
    --------------------------------------------------------------------
    -- 1) Build dynamic request body
    --------------------------------------------------------------------
    SET @body = N'{
      "messages": [
        {
          "role": "system",
          "content": "You are a business‑grade sentiment analyzer. Analyze the product’s reviews and return ONLY a JSON object with: sentiment_label (“positive”, “neutral”, “negative”), positive_score, neutral_score, negative_score, and feedback. The feedback must be one natural, human‑sounding, abstractive summary sentence that begins with “This product…”, keeps the full meaning of the original text, and uses a warm, positive, consumer‑friendly tone (e.g., great, good, decent, affordable) without inventing new facts. **All PII must be included exactly as written — do not remove, alter, shorten, or paraphrase any personal details**. Return no additional text."
        },
        {
          "role": "user",
          "content": "' + REPLACE(@text, '"', '\"') + '"
        }
      ]
    }';




    --------------------------------------------------------------------
    -- 2) Call Azure OpenAI
    --------------------------------------------------------------------
    EXEC sys.sp_invoke_external_rest_endpoint
        @method   = 'POST',
        @url      = 'https://<your azure openai name>.openai.azure.com/openai/deployments/<your deployment name>/chat/completions?api-version=<API_VERSION>',
        @headers  = '{"Content-Type":"application/json"}',
        @credential = [https://<your azure openai name>.openai.azure.com/],
        @payload  = @body,
        @response = @response OUTPUT;

    --------------------------------------------------------------------
    -- 3) Extract escaped JSON string
    --------------------------------------------------------------------
    SELECT @content = JSON_VALUE(@response, '$.result.choices[0].message.content');

    --------------------------------------------------------------------
    -- 4) Unescape JSON so SQL can parse it
    --------------------------------------------------------------------
    SELECT @json = REPLACE(REPLACE(@content, '\"', '"'), '"{', '{');
    SELECT @json = REPLACE(@json, '}"', '}');

    --------------------------------------------------------------------
    -- 5) Insert parsed sentiment into table
    --------------------------------------------------------------------
    INSERT INTO @sentiment
    SELECT
        @productid,
        JSON_VALUE(@json, '$.feedback'),
        JSON_VALUE(@json, '$.sentiment_label'),
        CAST(JSON_VALUE(@json, '$.positive_score') AS FLOAT),
        CAST(JSON_VALUE(@json, '$.neutral_score')  AS FLOAT),
        CAST(JSON_VALUE(@json, '$.negative_score') AS FLOAT);

    FETCH NEXT FROM review_cursor INTO @productid, @text;
END

CLOSE review_cursor;
DEALLOCATE review_cursor;

--------------------------------------------------------------------
-- 6) Final output
--------------------------------------------------------------------
SELECT * FROM @sentiment;
