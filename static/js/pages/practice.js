/* =========================================================
   NPTOR PRACTICE PAGE
   static/js/pages/practice.js

   Responsibilities:
   - Filter accordion
   - Submit practice answer via AJAX
   - Load next question via AJAX
   - Skip practice question via AJAX
   - Explanation toggle
   - Feedback submission
   - Loading state
   - Dynamic question/result replacement
   ========================================================= */

(function () {

    "use strict";


    /* =====================================================
       CONFIG
       ===================================================== */

    const config = window.PRACTICE_CONFIG || {};

    const container =
        document.getElementById("practiceContainer");

    const filterBody =
        document.getElementById("filterBody");

    const filterToggle =
        document.getElementById("filterToggle");

    const filterHint =
        document.getElementById("filterHint");

    const filterIcon =
        document.getElementById("filterToggleIcon");


    /* =====================================================
       CSRF
       ===================================================== */

    function getCookie(name) {

        let cookieValue = null;

        if (document.cookie && document.cookie !== "") {

            const cookies =
                document.cookie.split(";");

            for (let cookie of cookies) {

                cookie = cookie.trim();

                if (
                    cookie.startsWith(name + "=")
                ) {

                    cookieValue =
                        decodeURIComponent(
                            cookie.substring(
                                name.length + 1
                            )
                        );

                    break;
                }
            }
        }

        return cookieValue;
    }


    /* =====================================================
       FILTER UI
       ===================================================== */

    function updateFilterUI(expanded) {

        if (!filterHint || !filterIcon) {
            return;
        }

        if (expanded) {

            filterHint.textContent =
                "(Click to collapse)";

            filterIcon.textContent = "▴";

        } else {

            filterHint.textContent =
                "(Click to expand)";

            filterIcon.textContent = "▾";
        }
    }


    function setFilterState(expanded) {

        if (!filterBody) {
            return;
        }

        filterBody.classList.toggle(
            "is-open",
            expanded
        );

        localStorage.setItem(
            "practiceFilterExpanded",
            expanded ? "1" : "0"
        );

        updateFilterUI(expanded);
    }


    function initFilter() {

        if (!filterToggle || !filterBody) {
            return;
        }

        filterToggle.addEventListener(
            "click",
            function () {

                const expanded =
                    filterBody.classList.contains(
                        "is-open"
                    );

                setFilterState(!expanded);
            }
        );


        const savedState =
            localStorage.getItem(
                "practiceFilterExpanded"
            ) === "1";


        setFilterState(savedState);
    }


    /* =====================================================
       HTML REPLACEMENT
       ===================================================== */

    function replacePracticeContent(html) {

        if (!container) {
            return;
        }

        if (!html) {

            console.error(
                "Practice content is empty."
            );

            return;
        }

        container.innerHTML = html;


        /*
         * Because the content is dynamically replaced,
         * event delegation continues to work.
         *
         * Scroll only after the new content exists.
         */

        window.scrollTo({
            top: Math.max(
                container.offsetTop - 80,
                0
            ),
            behavior: "smooth"
        });
    }


    /* =====================================================
       LOADING STATE
       ===================================================== */

    function setLoading(isLoading) {

        if (!container) {
            return;
        }

        container.classList.toggle(
            "is-loading",
            isLoading
        );


        /*
         * Prevent duplicate submissions while
         * an AJAX request is running.
         */

        if (isLoading) {

            container.setAttribute(
                "aria-busy",
                "true"
            );

        } else {

            container.removeAttribute(
                "aria-busy"
            );
        }
    }


    /* =====================================================
       POST REQUEST
       ===================================================== */

    async function postForm(url, formData) {

        if (!url) {

            throw new Error(
                "Request URL is missing."
            );
        }


        /* -------------------------------------------------
           CSRF
           ------------------------------------------------- */

        const csrfToken =
            getCookie("csrftoken");


        const headers = {

            "X-Requested-With":
                "XMLHttpRequest"

        };


        if (csrfToken) {

            headers["X-CSRFToken"] =
                csrfToken;
        }


        /* -------------------------------------------------
           REQUEST
           ------------------------------------------------- */

        const response =
            await fetch(
                url,
                {
                    method: "POST",
                    headers: headers,
                    body: formData
                }
            );


        /* -------------------------------------------------
           READ RESPONSE BODY
           -------------------------------------------------

           Important:
           Django may return HTML when a 500 occurs
           instead of JSON.

           Therefore we read text first rather than
           immediately calling response.json().
        ------------------------------------------------- */

        const responseText =
            await response.text();


        /* -------------------------------------------------
           HTTP ERROR
           ------------------------------------------------- */

        if (!response.ok) {

            console.error(
                "NPTOR Practice AJAX HTTP Error",
                {
                    status: response.status,
                    statusText: response.statusText,
                    url: url,
                    response: responseText
                }
            );


            /*
             * Default error message.
             */

            let serverMessage =
                "Server returned HTTP " +
                response.status;


            /*
             * Try to extract useful information from
             * Django's DEBUG response.
             *
             * Django may return:
             *
             * Exception Type:
             * Exception Value:
             */

            if (responseText) {

                const exceptionTypeMatch =
                    responseText.match(
                        /Exception Type:\s*([^<\n]+)/i
                    );


                const exceptionValueMatch =
                    responseText.match(
                        /Exception Value:\s*([^<\n]+)/i
                    );


                if (exceptionTypeMatch) {

                    serverMessage =
                        exceptionTypeMatch[1].trim();
                }


                if (exceptionValueMatch) {

                    serverMessage +=
                        ": " +
                        exceptionValueMatch[1].trim();
                }
            }


            throw new Error(
                serverMessage
            );
        }


        /* -------------------------------------------------
           EMPTY RESPONSE
           ------------------------------------------------- */

        if (!responseText.trim()) {

            throw new Error(
                "Server returned an empty response."
            );
        }


        /* -------------------------------------------------
           JSON RESPONSE
           ------------------------------------------------- */

        try {

            return JSON.parse(
                responseText
            );

        } catch (error) {

            console.error(
                "NPTOR Practice AJAX returned invalid JSON",
                {
                    url: url,
                    response: responseText,
                    parseError: error
                }
            );


            throw new Error(
                "Server returned an invalid response."
            );
        }
    }


    /* =====================================================
       SUBMIT ANSWER
       ===================================================== */

    async function submitAnswer(form) {

        if (!form) {
            return;
        }


        if (!config.answerUrl) {

            console.error(
                "Practice answer URL is missing."
            );

            return;
        }


        /*
         * Prevent accidental double submission.
         */

        if (
            container &&
            container.classList.contains(
                "is-loading"
            )
        ) {
            return;
        }


        const formData =
            new FormData(form);


        const submitButton =
            form.querySelector(
                "button[type='submit']:not([name='skip'])"
            );


        if (submitButton) {

            submitButton.disabled = true;

            submitButton.setAttribute(
                "aria-busy",
                "true"
            );
        }


        setLoading(true);


        try {

            const data =
                await postForm(
                    config.answerUrl,
                    formData
                );


            if (data.success) {

                replacePracticeContent(
                    data.html
                );

            } else {

                alert(
                    data.message ||
                    "Unable to submit answer."
                );
            }


        } catch (error) {

            console.error(
                "Practice answer error:",
                error
            );


            /*
             * During development, show the actual
             * server-side error instead of hiding it.
             */

            alert(
                error?.message ||
                "Error submitting answer. Please try again."
            );


        } finally {

            setLoading(false);
        }
    }


    /* =====================================================
       NEXT QUESTION
       ===================================================== */

    async function loadNextQuestion() {

        if (!config.nextUrl) {

            console.error(
                "Practice next-question URL is missing."
            );

            return;
        }


        if (
            container &&
            container.classList.contains(
                "is-loading"
            )
        ) {
            return;
        }


        setLoading(true);


        try {

            const data =
                await postForm(
                    config.nextUrl,
                    new FormData()
                );


            /*
             * Some backend responses may redirect
             * when the practice session has ended.
             */

            if (data.redirect) {

                window.location.href =
                    data.redirect;

                return;
            }


            if (data.success) {

                replacePracticeContent(
                    data.html
                );

            } else {

                alert(
                    data.message ||
                    "Unable to load the next question."
                );
            }


        } catch (error) {

            console.error(
                "Next question error:",
                error
            );


            alert(
                error?.message ||
                "Error loading next question. Please try again."
            );


        } finally {

            setLoading(false);
        }
    }


    /* =====================================================
       SKIP QUESTION
       ===================================================== */

    async function skipQuestion() {

        if (!config.skipUrl) {

            console.error(
                "Practice skip URL is missing."
            );

            return;
        }


        if (
            container &&
            container.classList.contains(
                "is-loading"
            )
        ) {
            return;
        }


        setLoading(true);


        try {

            const data =
                await postForm(
                    config.skipUrl,
                    new FormData()
                );


            /* ---------------------------------------------
               COURSE REDIRECT
               --------------------------------------------- */

            if (data.redirect) {

                window.location.href =
                    data.redirect;

                return;
            }


            /* ---------------------------------------------
               NEXT QUESTION / COMPLETED
               --------------------------------------------- */

            if (data.success) {

                replacePracticeContent(
                    data.html
                );

            } else {

                alert(
                    data.message ||
                    "Unable to skip this question."
                );
            }


        } catch (error) {

            console.error(
                "Practice skip error:",
                error
            );


            alert(
                error?.message ||
                "Error skipping question. Please try again."
            );


        } finally {

            setLoading(false);
        }
    }


    /* =====================================================
       EXPLANATION
       ===================================================== */

    function toggleExplanation(button) {

        if (!button) {
            return;
        }


        const explanation =
            button.closest(
                ".practice-explanation"
            );


        if (!explanation) {
            return;
        }


        const box =
            explanation.querySelector(
                ".practice-explanation-content"
            );


        if (!box) {
            return;
        }


        const isHidden =
            box.hidden;


        box.hidden =
            !isHidden;


        button.setAttribute(
            "aria-expanded",
            isHidden
                ? "true"
                : "false"
        );


        button.textContent =
            isHidden
                ? "Hide Explanation"
                : "Show Explanation";
    }


    /* =====================================================
       FEEDBACK
       ===================================================== */

    async function submitFeedback(button) {

        if (!button) {
            return;
        }


        if (!config.feedbackUrl) {

            console.error(
                "Practice feedback URL is missing."
            );

            return;
        }


        const form =
            document.getElementById(
                "practiceForm"
            );


        if (!form) {

            console.error(
                "Practice form not found."
            );

            return;
        }


        const questionId =
            form.dataset.qid;


        if (!questionId) {

            alert(
                "Question ID is missing."
            );

            return;
        }


        const comment =
            document.getElementById(
                "studentComment"
            )?.value.trim() || "";


        const incorrect =
            document.getElementById(
                "answerIncorrect"
            )?.checked || false;


        if (!comment && !incorrect) {

            alert(
                "Please write a comment or mark the answer as incorrect/confusing."
            );

            return;
        }


        const formData =
            new FormData();


        formData.append(
            "question_id",
            questionId
        );


        formData.append(
            "student_comment",
            comment
        );


        if (incorrect) {

            formData.append(
                "answer_incorrect",
                "1"
            );
        }


        button.disabled = true;

        button.setAttribute(
            "aria-busy",
            "true"
        );


        try {

            const response =
                await postForm(
                    config.feedbackUrl,
                    formData
                );


            if (response.success) {

                button.textContent =
                    "Feedback Submitted";

                button.classList.add(
                    "is-submitted"
                );

            } else {

                alert(
                    response.message ||
                    "Unable to submit feedback."
                );

                button.disabled = false;
            }


        } catch (error) {

            console.error(
                "Feedback error:",
                error
            );


            alert(
                error?.message ||
                "Server error occurred while submitting feedback."
            );


            button.disabled = false;


        } finally {

            button.removeAttribute(
                "aria-busy"
            );
        }
    }


    /* =====================================================
       EVENT DELEGATION
       ===================================================== */

    function initEvents() {

        document.addEventListener(
            "click",
            function (event) {


                /* =========================================
                   PRACTICE SUBMIT
                   ========================================= */

                const submitButton =
                    event.target.closest(
                        "#practiceForm button[type='submit']"
                    );


                if (submitButton) {

                    /*
                     * Skip is now handled separately through
                     * the AJAX data-practice-skip button.
                     *
                     * Keep this check for backward
                     * compatibility with any old Skip button.
                     */

                    if (
                        submitButton.name ===
                        "skip"
                    ) {
                        return;
                    }


                    event.preventDefault();


                    const form =
                        document.getElementById(
                            "practiceForm"
                        );


                    if (form) {

                        submitAnswer(form);
                    }


                    return;
                }


                /* =========================================
                   SKIP QUESTION
                   ========================================= */

                const skipButton =
                    event.target.closest(
                        "[data-practice-skip]"
                    );


                if (skipButton) {

                    event.preventDefault();

                    skipQuestion();

                    return;
                }


                /* =========================================
                   NEXT QUESTION
                   ========================================= */

                const nextButton =
                    event.target.closest(
                        "[data-practice-next]"
                    );


                if (nextButton) {

                    event.preventDefault();

                    loadNextQuestion();

                    return;
                }


                /*
                 * Backward compatibility with the
                 * existing inline onclick:
                 *
                 * onclick="loadNextQuestion()"
                 *
                 * No action is needed here because
                 * loadNextQuestion is exposed globally.
                 */


                /* =========================================
                   EXPLANATION
                   ========================================= */

                const explanationButton =
                    event.target.closest(
                        ".practice-explanation-toggle"
                    );


                if (explanationButton) {

                    event.preventDefault();

                    toggleExplanation(
                        explanationButton
                    );

                    return;
                }


                /* =========================================
                   FEEDBACK
                   ========================================= */

                const feedbackButton =
                    event.target.closest(
                        "#feedbackSubmitBtn"
                    );


                if (feedbackButton) {

                    event.preventDefault();

                    submitFeedback(
                        feedbackButton
                    );

                    return;
                }

            }
        );
    }


    /* =====================================================
       INITIALIZATION
       ===================================================== */

    function init() {

        initFilter();

        initEvents();
    }


    /* =====================================================
       PUBLIC API
       ===================================================== */

    /*
     * The result partial currently uses:
     *
     * onclick="loadNextQuestion()"
     *
     * Therefore this function must be globally available.
     */

    window.loadNextQuestion =
        loadNextQuestion;


    /*
     * Optional public namespace.
     * Useful later if we remove inline handlers.
     */

    window.NPTORPractice = {

        submitAnswer,

        loadNextQuestion,

        skipQuestion,

        toggleExplanation,

        submitFeedback

    };


    /* =====================================================
       START
       ===================================================== */

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            init
        );

    } else {

        init();
    }

})();