document.addEventListener(
    "DOMContentLoaded",
    function () {

        const messages =
            document.querySelectorAll(
                ".message"
            );

        messages.forEach(
            function (message) {

                setTimeout(
                    function () {

                        message.style.opacity = "0";

                        setTimeout(
                            function () {
                                message.remove();
                            },
                            500
                        );

                    },
                    3500
                );

            }
        );

    }
);