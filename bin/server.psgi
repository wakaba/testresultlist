# -*- perl -*-
use strict;
use warnings;
use Path::Tiny;
use Wanage::URL;
use Wanage::HTTP;
use Warabe::App;
use Promised::Command;

$ENV{LANG} = 'C';
$ENV{TZ} = 'UTC';

my $RootPath = path (__FILE__)->parent->parent->absolute;

return sub {
  delete $SIG{CHLD} if defined $SIG{CHLD} and not ref $SIG{CHLD}; # XXX

  my $http = Wanage::HTTP->new_from_psgi_env ($_[0]);
  my $app = Warabe::App->new_from_http ($http);

  return $app->execute_by_promise (sub {
    my $path = [@{$app->path_segments}];

    $http->set_response_header
        ('Strict-Transport-Security' => 'max-age=2592000; includeSubDomains; preload');

    my $cmd = Promised::Command->new ([$RootPath->child ('perl'), $RootPath->child ("list.cgi")]);
    $cmd->envs->{REQUEST_METHOD} = $app->http->request_method;
    $cmd->envs->{QUERY_STRING} = $app->http->original_url->{query};
    $cmd->envs->{CONTENT_LENGTH} = $app->http->request_body_length;
    $cmd->envs->{CONTENT_TYPE} = $app->http->get_request_header ('Content-Type');
    $cmd->envs->{HTTP_ACCEPT_LANGUAGE} = $app->http->get_request_header ('Accept-Language');
    $cmd->envs->{PATH_INFO} = $app->http->url->{path};
    $cmd->stdin ($app->http->request_body_as_ref);
    my $stdout = '';
    my $out_mode = '';
    my $cgi_error;
    $cmd->stdout (sub {
      if ($out_mode eq 'body') {
        $app->http->send_response_body_as_ref (\($_[0]));
        return;
      }
      $stdout .= $_[0];
      while ($stdout =~ s/^([^\x0A]*[^\x0A\x0D])\x0D?\x0A//) {
        my ($name, $value) = split /:/, $1, 2;
        $name =~ tr/A-Z/a-z/;
        if (not defined $value) {
          warn "Bad CGI output: |$name|\n";
          $cgi_error = 1;
        } elsif ($name eq 'status') {
          my ($code, $reason) = split /\s+/, $value, 2;
          $app->http->set_status ($code, reason_phrase => $reason);
        } else {
          $app->http->set_response_header ($name => $value);
        }
      }
      if ($stdout =~ s/^\x0D?\x0A//) {
        $out_mode = 'body';
        $app->http->send_response_body_as_ref (\$stdout);
      }
    });
    return $cmd->run->then (sub {
      return $cmd->wait;
    })->then (sub {
      die $_[0] unless $_[0]->exit_code == 0;
      die "CGI output error" if $cgi_error;
      $app->http->close_response_body;
    });
  });
};

=head1 LICENSE

Copyright 2015 Wakaba <wakaba@suikawiki.org>.

This library is free software; you can redistribute it and/or modify
it under the same terms as Perl itself.

=cut
