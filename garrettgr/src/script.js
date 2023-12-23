const printLine = (text) => {
    let lastRowText = $('#output-table tbody tr:last td').text();
    let secondToLastRowText = $('#output-table tbody tr:nth-last-child(2) td').text();
    if (text !== lastRowText && text !== secondToLastRowText) {
        $('#output-table tbody').append('<tr><td>' + text + '</td></tr>');
    }
};

const setLocation = (loc, time) => {
    $("#position_display h5:first").text(loc['name']);
    $("#position_display h5:last").text(time);

    $('#direction').children().each(function() {
        $(this).children().prop('disabled', true);
        $(this).children().removeClass('btn-info');
        $(this).children().addClass('disabled');
        $(this).children().addClass('btn-secondary');

    });
    Object.keys(loc['connections']).forEach(function(connection) {
        let btn = $(`#${connection}_btn`);
        btn.prop('disabled', false);
        btn.removeClass('disabled');
        btn.removeClass('btn-secondary');
        btn.addClass('btn-info');
    });
    
};

const removeWhitespace = (userInput) => {
    return userInput.replace(/\s+/g, ' ').trim();
}

const addKeyWords = (keyWords, type) => {
    if (Array.isArray(keyWords) && keyWords.every(element => typeof element === 'string')) {
        keyWords.forEach(function(keyWord) {
            let listItem = $('<li>');
            let button = $('<button>').text(keyWord);
            button.click(function() {
                userInput = $('#user-input').val();
                if (!userInput.includes(keyWord)) {
                    userInput = removeWhitespace(userInput + ' ' + keyWord);
                    $('#user-input').val(userInput);
                }
            });

            button.addClass('btn btn-outline-secondary');
            listItem.append(button);

            let existingListItem = $(`#${type} li:contains(${keyWord})`);
            if (existingListItem.length === 0) {
                $(`#${type}`).append(listItem);
            }
        });
    } else {
        console.error('Invalid input. Expected an array of strings.');
    }

};

const addDirections = (() => {
    directions = ['North', 'South', 'East', 'West'];
    directions.forEach(function(direction) {
        let listItem = $('<li>');
        let button = $('<button>').text(direction);
        button.click(function() {
            userInput = $('#user-input').val();
            if (!userInput.includes(direction)) {
                userInput = removeWhitespace(userInput + ' ' + direction);
                $('#user-input').val(userInput);
            }
        });
        button.addClass('btn btn-outline-secondary');
        listItem.append(button);

        let existingListItem = $(`#nouns li:contains(${direction})`);
        if (existingListItem.length === 0) {
            $('#nouns').append(listItem);
        }
    });
    $('#direction').on('click', 'button', function() {
        let direction = $(this).data('direction');
        userInput = $('#user-input').val();
        if (!userInput.includes(direction)) {
            userInput = userInput + ' ' + direction;
            if (!userInput.includes('Go')) {
                userInput = removeWhitespace('Go ' + userInput);
                $('#user-input').val(userInput);
            } else {
                userInput = removeWhitespace(userInput);
                $('#user-input').val(userInput);
            }
        }
    });
});

const addNouns = (data) => {
    let nouns = [];

    if (data.player['inventory']) {
        data.player['inventory'].forEach(function(item) {
            nouns.push(item['name']);
        });
    }
    if (data.player['location']) {
        nouns.push(data.player['location']['name']);
        if (data.player['location']['items']) {
            data.player['location']['items'].forEach(function(item) {
                nouns.push(item['name']);
            });
        }
        if (data.player['location']['characters']) {
            data.player['location']['characters'].forEach(function(character) {
                nouns.push(character['name']);
            });
        }
    }
    addDirections();
    addKeyWords(nouns, 'nouns');
};

const showHealth = (health) => {
    $("#health_bar i").hide();
    for (let i = 1; i <= health; i++) {
        $(`#heart_${i}`).show();
    }
};

$(document).ready(function() {
    var json = {};
    let requests = 0;

    const updatePage = (data) => {
        $('#nouns').empty();
        addNouns(data);
        printLine(data.history['prompt_outputs'][data.history['prompt_outputs'].length - 1]);
        setLocation(data.player['location'], data.player['input_position']);
        showHealth(data.player['health']);
    };

    const sendRequest = (userInput, destination, callback) => {
        requests++;
        
        $.ajax({
            url: `/flask/${destination}`,
            type: 'POST',
            data: JSON.stringify({userInput: userInput}),
            contentType: 'application/json',
            success: function(response) {
                console.log("Response: ", response);
                callback(response);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.log("Error: " + errorThrown);
                try {
                    let response = JSON.parse(jqXHR.responseText);
                    console.log("Response: ", response);
                } catch(e) {
                    console.log("Could not parse JSON: ", jqXHR.responseText);
                }
            }
        });
        //busy work to keep the server from using other process... kinda works?
        //! NOT REALLY WORKING
        // $.ajax({
        //     url: '/flask/second-process',
        //     type: 'POST',
        //     data: 'heyyyy',
        //     contentType: 'application/json',
        //     success: function(response) {
        //         console.log(`Second process did... ${response}`);
        //     }
        // });
    };

    let verbs = ['Examine', 'Take', 'Drop', 'Use', 'Go', 'Inventory', 'Help'];
    addKeyWords(verbs, 'verbs');
    sendRequest('', 'reset', function(response) {
        json = response;
        updatePage(json);
    });

    $('#save_point_btn').click(function() {
        sendRequest('', 'save', function() {
            alert('Game save successful');
        });
    });

    $('#load_save_btn').click(function() {
        sendRequest('', 'load', function(response) {
            json = response;
            updatePage(json);
            $('#output-table tbody').empty();
            printLine(json.history['prompt_outputs'][0]);
            for (let i = 0; i < json.history['user_inputs'].length; i++) {
                printLine(json.history['user_inputs'][i]);
                printLine(json.history['prompt_outputs'][i+1]);
            }
            alert('Game loaded successfully');
        });
    });

    $('#submit-btn').click(function() {
        let userInput = $('#user-input').val();
        userInput = removeWhitespace(userInput);

        if (userInput.trim() === '') {
            console.log('User input is blank. Rejecting submission.');
            return;
        }
        if (json.history['user_inputs'] && json.history['user_inputs'].length > 0 && userInput === json.history['user_inputs'][json.history['user_inputs'].length - 1]) {
            console.log('User input is the same as the last input. Rejecting submission.');
            return;
        }

        printLine(userInput);

        //? maybe have it send a blank request every other request to keep the server from using other processes?
        // if (requests % 2 == 0) {
        //     sendRequest('', 'post', function() {
        //         console.log('Second process finished');
        //     });
        // }

        //? always send a blank request first?
        sendRequest('', 'post', function() {
            console.log('Blank request finished');
        });

        sendRequest(userInput, 'post', function(response) {
            json = response;
            updatePage(json);
        });

        $('#user-input').val('');
    });

    $('#user-input').keypress(function(e) {
        if (e.which === 13) {
            $('#submit-btn').click();
        }
    });

    $('#inv_btn').click(function() {
        printLine('Inventory');
        if (json.player['inventory'].length === 0) {
            printLine('Your pockets are empty');
        } else {
            printLine(`You have ${json.player['inventory'].length} items in your inventory: ${json.player['inventory'].map(item => item.name).join(', ')}`);
        }
    });

    $('#clear_btn').click(function() {
        $('#output-table tbody').empty();
        $('#user-input').val('');
        userInput = $('#user-input').val();
        updatePage(json);
    });
});