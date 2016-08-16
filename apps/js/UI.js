/**
UI library for TXT apps
*/
var UI={

    setup:function(config)
    {
        UI.tabs = config.tabs;
        UI.dialogs = config.dialogs;

        setup_help();
        setup_UI();
        setup_actions();
        setup_functions();
        UI.switch_tab(Object.keys(UI.tabs)[0]);

        function setup_help()
        {
            operation('help', '', function(help)
            {
                $('#api_help').append($('<p>').html('http POST endpoints. To experiment, open the js console and <code>operation("endpoint", {param:"value"}, notify)</code>.'));
                for( var fun in help)
                {
                    $('#api_help').append($('<h4>').text(fun));
                    var parts = help[fun].split('\n\n');
                    var desc = parts[0];
                    var text = parts.slice(1).join('\n\n');
                    $('#api_help').append($('<p>').text(desc));
                    if( text)
                        $('#api_help').append($('<pre>').text(text));
                }
            });
        }
        function setup_UI()
        {
            for (var tab in UI.tabs)
            {
                setup_tab(tab, UI.tabs[tab]);
            }

            //tab switching
            $('#navbar a').each(function()
            {
                if( $(this).data('tab'))
                {
                    var target = $(this).data('tab');
                    $(this).click(function(){
                        UI.switch_tab(target);
                    });
                }
            });
        }
        function setup_tab(name, config)
        {
            if (config.panels)
            {
                for (var pan in config.panels)
                    setup_panel(pan, config.panels[pan]);
            }
        }
        function setup_panel(name, config)
        {
            set_panel_width($('#'+name), config.width || 6, config.widable);
        }
        function set_panel_width(panel, width, widable)
        {
            var col = panel.parent();
            col.addClass('col-md-'+width);
            if (widable)
            {
                panel.find('.panel-heading').append('<button type="button" class="btn btn-xs btn-default pull-right widen" style="display:inline-block"><span class="glyphicon glyphicon-resize-horizontal"></span></button>')
                panel.find('.panel-heading .widen').click(function()
                {
                    if( col.hasClass('col-md-'+width))
                        col.removeClass('col-md-'+width).addClass('col-md-12');
                    else
                        col.removeClass('col-md-12').addClass('col-md-'+width);
                });
            }
        }
        function setup_actions()
        {
            var time = 0;
            setInterval(function()
            {
                for (var tab in UI.tabs)
                {
                    if (UI.tabs[tab].actions)
                    {
                        for( var i=0; i<UI.tabs[tab].actions.length; i++)
                        {
                            var act = UI.tabs[tab].actions[i];
                            if (document.visibilityState=='visible')
                            if (UI.active_tab==tab || UI.all_tabs_active)
                            if (act.periodic && time%act.periodic===0)
                                UI.perform_action(act);
                        }
                    }
                }
                time++;
            }, 1000);

            for (var dia in UI.dialogs)
            {
                setup_dialog_action(dia, UI.dialogs[dia]);
            }
        }
        function setup_dialog_action(name, dialog)
        {
            $('#'+name).find('.action').click(function()
            {
                var arr = $('#'+name).find('form').serializeArray();
                if (dialog.action_param_as_object)
                {
                    var par = {};
                    var params = [par];
                    for (var i=0; i<arr.length; i++)
                    {
                        par[arr[i].name] = arr[i].value;
                    }
                }
                else
                {   //default as array
                    var params = [];
                    for (var i=0; i<arr.length; i++)
                    {
                        params.push(arr[i].value);
                    }
                }
                if (dialog.action.apply(null, params))
                    $('#'+name).modal('hide');
            });
        }
        function setup_functions()
        {
            if( $('#server_restart').length)
                $('#server_restart').click(function()
                {
                    if( confirm("Restart?"))
                    operation('restart_request', '', function(res)
                    {
                        notify(res);
                        operation('restart_request', '', function(){});
                        setTimeout(function(){
                            window.location.reload();
                        }, 4000);
                    });
                });

            if( $('#server_update').length)
                $('#server_update').click(function()
                {
                    operation('server_update', '', function(res)
                    {
                        notify(res);
                    });
                });
        }
    },

    switch_tab:function(target)
    {
        $('#tabs > div').each(function()
        {
            if( target===$(this).attr('id'))
                $(this).show();
            else
                $(this).hide();
        });
        $('#navbar a').each(function()
        {
            if( $(this).data('tab'))
            {
                if( target===$(this).data('tab'))
                    $(this).parent().addClass('active');
                else
                    $(this).parent().removeClass('active');
            }
        });
        UI.active_tab = target;
        activate_tab(target);

        function activate_tab(tab)
        {
            if (UI.tabs[tab].actions)
            {
                for( var i=0; i<UI.tabs[tab].actions.length; i++)
                {
                    var act = UI.tabs[tab].actions[i];
                    UI.perform_action(act);
                }
            }
        }
    },

    perform_action:function(act)
    {
        operation(act.oper, act.param || '', act.action);
    }
};

function notify(data)
{
    if (data.message)
        $.notify({
            message: format(data.message)
        },{
            type: 'success'
        });
    else if (data.exception)
        $.notify({
            message: format(data.exception)
        },{
            type: 'danger'
            /*placement: {
                from: 'top',
                align: 'center'
            }*/
        });
    console.log(data);

    function format(str) {
        if (typeof str==='string')
            return str.split('\n').join('<br>');
        else if( str instanceof Array)
            return str.join('<br>');
        else
            return str;
    }
}

function operation(command, param, callback)
{
    var This=this;
    if (!This.running)
        This.running = {}
    var command_param = command+JSON.stringify(param);
    if (!This.running[command_param])
    {
        This.running[command_param] = true;
        $.ajax(command, {
            data: JSON.stringify(param),
            dataType: 'json',
            method: 'POST',
            success: function(data)
            {
                This.running[command_param] = false;
                callback(data);
                if (data.force_restart)
                    window.location.reload();
            },
            error: function(handle, A, B)
            {
                This.running[command_param] = false;
                notify({
                    'exception': A+' '+B
                });
            }
        });
    }
}

/*
from
{
    item1: [1, 2, 3],
    item2: [2, 3, 4],
}
to
[
    [item, 1, 2, 3],
    [item, 2, 3, 4],
]
*/
function transform(data)
{
    var trans = [];
    for (var i in data)
        if (typeof data[i] == 'string')
            trans.push([i, data[i]]);
        else
            trans.push(([i]).concat(data[i]));
    return trans;
}

function check(data)
{
    if (data.exception)
    {
        return {}
    }
    return data;
}

function make_table(table, data, empty_message, key_field, action, action_callback, options)
{
    if (!this.cache)
        this.cache = {}
    if (JSON.stringify(this.cache[table.selector])===JSON.stringify(data))
        return;
    this.cache[table.selector] = data;
    if (!data.push)
        data = transform(data);
    var count = data.length;
    var obj = {
        navigation: (count<10?0:3),
        columnSelection: true,
        rowCount: [15, -1],
        caseSensitive: false,
        labels: {
            noResults: empty_message
        },
        formatters: {
            'action': function(col, row)
            {
                return action_button(row[key_field], action.icon, action.tooltip, action.text);
            },
            'progress': function(col, row)
            {
                var per = Math.round(row.progress*100);
                return '<div class="progress"><div class="progress-bar" style="min-width: 3em; width: '+per+'%;">'+per+'%</div></div>'
            }
        }
    };
    if (options)
    {
        for (oo in options)
        {
            if (typeof obj[oo]==='object')
                $.extend(obj[oo], options[oo]);
            else
                obj[oo] = options[oo];
        }
    }
    var grid = render_table(table, data)
    .bootgrid(obj).on('loaded.rs.jquery.bootgrid', function()
    {
        //grid.find('th[data-column-id="action"]').data('formatter', 'action');
        /* Executes after data is loaded and rendered */
        grid.find('.action').off('click').on('click', function(e)
        {
            action_callback($(this).data('id'))
        });
    });
}

function render_table(table, data)
{
    var html = '';
    for( var i=0; i<data.length; i++)
    {
        html += '<tr>';
            for( var j=0; j<data[i].length; j++)
            {
                html += '<td>';
                    html += data[i][j];
                html += '</td>';
            }
        html += '</tr>';
    }
    table.find('tbody').html(html);
    return table;
}

function action_button(id, icon, tooltip, text)
{
    return '<button type="button" title="'+tooltip+'" class="btn btn-xs btn-default action" data-id="' + id + '">' + (text?text+' ':'') + '<span class="glyphicon glyphicon-' + icon + '"></span></button>';
}
