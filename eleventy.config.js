export default function (eleventyConfig) {
    eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
    eleventyConfig.addPassthroughCopy({ "src/downloads": "downloads" });

    eleventyConfig.addPassthroughCopy({
        "src/favicon.ico": "favicon.ico",
    });

    eleventyConfig.addCollection("sitemapPages", (collectionApi) =>
        collectionApi
            .getAll()
            .filter(
                (item) =>
                    item.data.layout === "layouts/base.njk" &&
                    item.data.robots !== "noindex, follow",
            )
            .sort((first, second) =>
                first.url < second.url ? -1 : first.url > second.url ? 1 : 0,
            ),
    );

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
