export default function (eleventyConfig) {
    eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
    eleventyConfig.addPassthroughCopy({ "src/downloads": "downloads" });

    eleventyConfig.addPassthroughCopy({
        "src/favicon.ico": "favicon.ico",
    });

    return {
        dir: {
            input: "src",
            output: "html",
            includes: "_includes",
        },
        htmlTemplateEngine: "njk",
        templateFormats: ["njk"],
    };
}
