from backend.providers.sources.quality import classify_source_type, source_quality_score


def test_unknown_site_docs_path_is_not_treated_as_high_quality_documentation():
    source_type = classify_source_type(
        "https://trainingsites.io/docs/10-ways-to-use-gemini-2-5-pro-with-multimodal-inputs/",
        "10 Ways To Use Gemini 2.5 Pro with Multimodal Inputs",
    )

    assert source_type == "unknown"
    assert source_quality_score(source_type) == 0.2


def test_google_developer_docs_and_blogs_are_official_sources():
    assert classify_source_type("https://ai.google.dev/gemini-api/docs/agents", "Agents Overview") == "official"
    assert classify_source_type("https://developers.googleblog.com/real-world-agent-examples-with-gemini-3/", "Real-World Agent Examples") == "official"




def test_known_blog_platforms_are_tagged_blog():
    # Domain-based recognition for common blogging platforms.
    assert classify_source_type("https://dev.to/kuldeep_paul/ten-failure-modes-of-rag", "Ten failure modes") == "blog"
    assert classify_source_type("https://alwyns2508.medium.com/what-actually-breaks", "What breaks") == "blog"
    assert classify_source_type("https://example.substack.com/p/my-post", "My post") == "blog"
    assert classify_source_type("https://userblog.hashnode.dev/a-post", "A post") == "blog"
    assert classify_source_type("https://myblog.wordpress.com/2025/01/01/post", "") == "blog"


def test_url_path_heuristic_catches_company_blog_posts():
    # Custom company domains whose URL path strongly indicates a blog post.
    # Previously these fell through to "unknown" and dragged the confidence
    # metric down despite their content being perfectly fine for citations.
    assert classify_source_type(
        "https://www.getmaxim.ai/articles/rag-evaluation-a-complete-guide-for-2025/",
        "RAG Evaluation Complete Guide",
    ) == "blog"
    assert classify_source_type(
        "https://dextralabs.com/blog/production-rag-in-2025-evaluation-cicd-observability/",
        "Production RAG in 2025",
    ) == "blog"
    assert classify_source_type(
        "https://company.com/insights/market-analysis-2025",
        "Market analysis",
    ) == "blog"


def test_classifier_does_not_regress_existing_official_and_paper_cases():
    # Sanity regression: unchanged behavior for arxiv, official, and unknown
    # docs paths that the classifier has always gotten right.
    assert classify_source_type("https://arxiv.org/abs/2401.00001", "Paper", provider="arxiv") == "paper"
    assert classify_source_type("https://developer.nvidia.com/cuda-toolkit", "CUDA") == "official"
    assert classify_source_type(
        "https://trainingsites.io/docs/how-to-train-your-llm",
        "Training Docs",
    ) == "unknown"




def test_academic_paper_hosts_are_tagged_paper():
    # Exact IEEE URL that was 'unknown' in the R3 live run.
    assert classify_source_type(
        "https://ieeexplore.ieee.org/abstract/document/10852457",
        "Some IEEE paper",
    ) == "paper"
    # Exact alphaxiv URL from R3.
    assert classify_source_type(
        "https://www.alphaxiv.org/overview/2501.10734v1",
        "An arxiv paper",
    ) == "paper"
    # Broader academic hosts that realistic live searches surface.
    assert classify_source_type("https://openreview.net/forum?id=abc123", "OR paper") == "paper"
    assert classify_source_type("https://aclanthology.org/2025.coling-main.449.pdf", "ACL paper") == "paper"
    assert classify_source_type("https://dl.acm.org/doi/10.1145/abc", "ACM Digital Library") == "paper"
    assert classify_source_type("https://link.springer.com/article/10.1007/abc", "Springer") == "paper"
    assert classify_source_type("https://www.nature.com/articles/s41586-024-12345", "Nature paper") == "paper"
    assert classify_source_type("https://jmlr.org/papers/v25/23-0123.html", "JMLR paper") == "paper"
    assert classify_source_type("https://ai.jmir.org/2025/1/e75262", "JMIR AI") == "paper"


def test_paper_hosts_score_higher_than_blogs():
    # Sanity: the quality score for paper domains beats blog domains.
    assert source_quality_score("paper") > source_quality_score("blog")
    assert source_quality_score("paper") == 0.85


def test_code_repo_hosts_are_tagged_repo():
    # Exact GitHub URL that was 'unknown' in R3.
    assert classify_source_type(
        "https://github.com/pete-builds/research-reports/blob/main/rag-failure-modes-and-evaluation.md",
        "RAG failure modes",
    ) == "repo"
    # Other common code hosts.
    assert classify_source_type("https://gitlab.com/someorg/someproj", "project") == "repo"
    assert classify_source_type("https://bitbucket.org/someorg/proj", "project") == "repo"
    assert classify_source_type("https://codeberg.org/user/repo", "") == "repo"


def test_repo_quality_score_sits_between_blog_and_news():
    # Repos are higher-signal than blogs (code/docs authored by maintainers)
    # but lower than peer-reviewed papers or vendor-official documentation.
    assert source_quality_score("repo") == 0.55
    assert source_quality_score("repo") > source_quality_score("blog")
    assert source_quality_score("repo") < source_quality_score("paper")


def test_arxiv_provider_still_classifies_as_paper_even_for_plain_host():
    # Preserves existing behavior: provider='arxiv' wins even if the URL host
    # would otherwise fall through to another branch.
    assert classify_source_type("https://random.example/some-path", "title", provider="arxiv") == "paper"
