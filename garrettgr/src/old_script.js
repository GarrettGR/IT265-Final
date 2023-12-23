const resetData = (callback) => {
    $.ajax({
        url: '/flask/reset',
        type: 'GET',
        success: function(response) {
            console.log(response);
            callback(response);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.log("Error: " + errorThrown);
        }
    });
};

printLine = (text) => {
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

function removeWhitespace(userInput) {
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

const getData = (callback) => {
    $.ajax({
        url: '/flask/json',
        type: 'GET',
        dataType: 'json',
        success: function(data) {
            console.log(data);
            callback(data);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.log("Error: " + errorThrown);
            try {
                var response = JSON.parse(jqXHR.responseText);
                console.log("Response: ", response);
            } catch(e) {
                console.log("Could not parse JSON: ", jqXHR.responseText);
            }
        }
    });
};

const showHealth = (health) => {
    $("#health_bar i").hide();
    for (let i = 1; i <= health; i++) {
        $(`#heart_${i}`).show();
    }
};

const updatePage = (data) => {
    addNouns(data);
    printLine(data.history['prompt_outputs'][data.history['prompt_outputs'].length - 1]);
    setLocation(data.player['location'], data.player['input_position']);
    showHealth(data.player['health']);
};

// -------------------------------------------------------------------------

$(document).ready(function() {

    $('#user-input').val('');
    var userInput = $('#user-input').val();
    let verbs = ['Examine', 'Take', 'Drop', 'Use', 'Go', 'Inventory', 'Help'];
    var json = {};

    addKeyWords(verbs, 'verbs');
    resetData(function(response) {
        json = response;
        updatePage(json);
    });

    $('#save_point_btn').click(function() {
        $.ajax({
            url: '/flask/save',
            type: 'GET',
            success: function() {
                alert('Game save successful');
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.log("Error: " + errorThrown);
            }
        });
    });

    $('#load_save_btn').click(function() {
        $.ajax({
            url: '/flask/load',
            type: 'GET',
            success: function() {
                getData(function(data) {
                    json = data;
                    updatePage(json);
                    $('#output-table tbody').empty(); // Remove the rows from the table body
                    printLine(json.history['prompt_outputs'][0]);
                    for (let i = 0; i < json.history['user_inputs'].length; i++) {
                        printLine(json.history['user_inputs'][i]);
                        printLine(json.history['prompt_outputs'][i+1]);
                    }
                    alert('Game loaded successfully');
                });
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.log("Error: " + errorThrown);
            }
        });
    });


    $('#submit-btn').click(function() {
        userInput = $('#user-input').val();
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

        $.ajax({
            url: '/flask/post',
            type: 'POST',
            data: JSON.stringify({userInput: userInput}),
            contentType: 'application/json',
            success: function(response) {
                getData(function(data) {
                    json = data;
                    updatePage(json);
                });
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.log("Error: " + errorThrown);
                try {
                    var response = JSON.parse(jqXHR.responseText);
                    console.log("Response: ", response);
                } catch(e) {
                    console.log("Could not parse JSON: ", jqXHR.responseText);
                }
            }
        });

        $('#user-input').val('');
        userInput = $('#user-input').val();
    });

    $('#user-input').keypress(function(e) {
        if (e.which === 13) {
            $('#submit-btn').click();
        }
    });

    $('#inv_btn').click(function() {
        printLine('Inventory:');
        if (json.player['inventory'].length === 0) {
            printLine('Your pockets are empty');
        } else {
            json.player['inventory'].forEach(function(item) {
                printLine(item.name);
            });
        }
    });

    $('#clear_btn').click(function() {
        $('#output-table tbody').empty();
        $('#user-input').val('');
        userInput = $('#user-input').val();
        updatePage(json);
    });
});