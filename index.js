class pythonLib {
    constructor() {
        process.env.Path += `${__dirname}\\node_modules\\dharma-python-lib\\python3`;
        (async() => {
        })();
    }
}

module.exports = new pythonLib();