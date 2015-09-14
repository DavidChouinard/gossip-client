$(document).ready(function() {

  $("time.timeago").timeago();

  var wavesurfers = [].map.call($('.list-group-item-wave'), function (element) {
    var wavesurfer = Object.create(WaveSurfer);

    wavesurfer.init({
      container: element,
      waveColor: '#FF8008',
      progressColor: '#E87407',
      normalize: true,
      height: 40
    });

    wavesurfer.load($(element).parent().parent().data('audio-url'));

    return wavesurfer;
  });

  $('.list-group-item').on('click', function(e) {
    if (!$(this).hasClass('active')) {
      e.stopPropagation();
      $(this).addClass('active');
    }

    $(this).siblings().removeClass('active');

    $(this).find('.list-group-item-icon-play').hide();
    $(this).find('.list-group-item-icon-pause').show();
    wavesurfers[$(this).index()].play();

    $(this).siblings().find('.list-group-item-icon-play').show();
    $(this).siblings().find('.list-group-item-icon-pause').hide();

    for (i = 0; i < wavesurfers.length; i++) {
      if (i == $(this).index()) {
        continue
      }
      wavesurfers[i].stop();
    }
  });

  $('.list-group-item-icon-pause').on('click', function(e) {
    e.stopPropagation();
    console.log("clicked pause");

    $(this).parent().find('.list-group-item-icon-play').show();
    $(this).hide();

    console.log($(this).parent().parent().index());
    wavesurfers[$(this).parent().parent().index()].pause();
  });

  $('.alert-action').on('click', function(e) {
    e.preventDefault();

    $(this).parent().hide();
    $(this).parent().next().slideDown('fast');
  });

});
