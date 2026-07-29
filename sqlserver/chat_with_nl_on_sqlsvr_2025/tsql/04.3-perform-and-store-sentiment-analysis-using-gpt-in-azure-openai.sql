/* ***************************************************************************
    PERFORM AND STORE SENTIMENT ANALYSIS USING GPT IN AZURE OPENAI

    During the process, make sure you take pii (Personally Identifiable Information) seriously.
     - Do not remove, alter, or modify any personal details.
     - make sure to maintain end to end integrity.
     - Ensure that all data is handled in compliance with relevant regulations and policies.
     - batch processing is preferred for large datasets., feel free to modify the script as needed.

     - can take up to 2 minutes to complete.
******************************************************************************/
USE [TestDB];
GO

-- Truncate that table
TRUNCATE TABLE dbo.product_review_summary;
GO

-- Variables reused for each product
DECLARE @productid INT;
DECLARE @text NVARCHAR(MAX);
DECLARE @body NVARCHAR(MAX);
DECLARE @response NVARCHAR(MAX);
DECLARE @content NVARCHAR(MAX);
DECLARE @json NVARCHAR(MAX);

-- Cursor over aggregated reviews
DECLARE review_cursor CURSOR FOR
    SELECT 
        p.productid,
        STRING_AGG(r.review_text, ' ') AS combined_reviews
    FROM products AS p
    INNER JOIN product_reviews AS r ON p.productid = r.productid
    --WHERE p.productid in(1,2,18)
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
        @url      = 'https://az-openai-live-demo-01.openai.azure.com/openai/deployments/gpt-5.4-nano/chat/completions?api-version=2024-02-15-preview',
        @headers  = '{"Content-Type":"application/json"}',
        @credential = [https://az-openai-live-demo-01.openai.azure.com/],
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
    INSERT INTO dbo.product_review_summary (
        productid,
        abstractive_summary,
        sentiment_label,
        positive_score,
        neutral_score,
        negative_score
    )
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
SELECT TOP (5) * FROM dbo.product_review_summary;
GO